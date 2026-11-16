"""Train/evaluate frozen Qwen3 with bottleneck adapters or matched-budget LoRA."""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup
from evaluation import dumps, score, aggregate

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = '''你负责将中文要求转换成 JSON Schema 和具体 JSON 数据。只输出一个 JSON 对象，恰好包含 schema 和 data 两个键，两者值均为对象。先输出 schema，再输出 data；不要输出解释、Markdown代码块或思考过程。
Schema 根对象必须包含 "$schema": "https://json-schema.org/draft/2020-12/schema" 和 "type": "object"，不得省略这两个声明。字段名严格按请求给出的英文名。除明确可选或条件必填的字段外，字段默认必填；对象默认禁止额外字段。姓名、文本、电话和标识符是字符串，保留前导零。数组按输入顺序排列。明确说恰好几项时设置数组最小和最大长度为该数；具体姓名、日期、电话等实例值不自动成为 const 规则。不要添加未要求的范围、枚举或长度限制。明确要求缺失值用 null 时，字段类型必须允许 null。相对日期根据提供的参考日期和时区换算。
支持基本类型、properties、required、additionalProperties、items、minItems/maxItems、enum、minimum/maximum、minLength/maxLength、pattern、format、if/then/else、dependentRequired、oneOf/anyOf/allOf和明确要求的const；不使用引用。条件字段必须在properties中声明，区分无条件必填和条件必填。数据必须忠实于请求并通过生成的Schema。
普通口语会议请求未指定字段名时，固定输出 start_time（带时区的date-time字符串）、location（原文地点字符串）、participants（参会者对象数组，每项只有name和phone两个字符串字段）。这三个会议字段以及每人的name/phone均必填，所有对象禁止额外字段；participants最小最大长度均为明确的参会人数。不要自行添加会议标题等字段。'''

def read_rows(split,limit=0):
    rows = [json.loads(l) for l in (ROOT/'data'/f'{split}.jsonl').read_text(encoding='utf-8').splitlines() if l]
    if limit and limit < len(rows):
        # Fixed, evenly spaced indices cover generators that emit contiguous families.
        rows = [rows[i] for i in np.linspace(0,len(rows)-1,limit,dtype=int)]
    return rows

def read_suites(split):
    with gzip.open(ROOT/'data'/f'{split}_witnesses.jsonl.gz','rt',encoding='utf-8') as f:
        return {r['id']:r for r in map(json.loads,f)}

def target(row):
    return json.dumps({'schema':row['reference_schema'],'data':row['reference_data']},
                      ensure_ascii=False,separators=(',',':'))

def messages(row, examples=None):
    result = [{'role':'system','content':SYSTEM}]
    for example in examples or []:
        result += [{'role':'user','content':example['input']},
                   {'role':'assistant','content':target(example)}]
    result += [{'role':'user','content':row['input']}]
    return result

class Bottleneck(nn.Module):
    def __init__(self,hidden,width):
        super().__init__()
        self.down = nn.Linear(hidden,width)
        self.up = nn.Linear(width,hidden)
        nn.init.normal_(self.down.weight,std=0.02)
        nn.init.zeros_(self.down.bias)
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)
    def forward(self,h):
        # FP32 trainable weights/Adam moments, BF16 frozen backbone activations.
        return (h.float()+self.up(torch.nn.functional.silu(self.down(h.float())))).to(h.dtype)

def adapter_hook(module,inputs,output):
    if isinstance(output,tuple):
        return (module.task_adapter(output[0]),)+output[1:]
    return module.task_adapter(output)

def build(args):
    manifest = json.loads((ROOT/'model_manifest.json').read_text())
    tokenizer = AutoTokenizer.from_pretrained(manifest['local_path'],local_files_only=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'left'
    model = AutoModelForCausalLM.from_pretrained(manifest['local_path'],local_files_only=True,
        dtype=torch.bfloat16,attn_implementation='sdpa',device_map={'':'cuda:0'})
    for p in model.parameters():
        p.requires_grad_(False)
    if args.method == 'adapter':
        for layer in model.model.layers:
            layer.add_module('task_adapter',Bottleneck(model.config.hidden_size,args.width).to(device='cuda',dtype=torch.float32))
            layer.register_forward_hook(adapter_hook)
    elif args.method == 'lora':
        from peft import LoraConfig,get_peft_model
        model = get_peft_model(model,LoraConfig(r=16,lora_alpha=32,lora_dropout=0.,
            target_modules=['q_proj','k_proj','v_proj','o_proj'],bias='none',task_type='CAUSAL_LM'))
    if args.checkpoint:
        state = torch.load(args.checkpoint,map_location='cpu',weights_only=True)
        names = set(dict(model.named_parameters()))
        expected_names={n for n,p in model.named_parameters() if p.requires_grad}
        if set(state) != expected_names or not set(state)<=names:
            raise ValueError('checkpoint must contain exactly all trainable parameters')
        model.load_state_dict(state,strict=False)
    return model,tokenizer,manifest

def save_trainable(model,path):
    state = {n:p.detach().cpu().clone() for n,p in model.named_parameters() if p.requires_grad}
    torch.save(state,path)

def evaluate(model,tokenizer,rows,suites,args,outfile,examples=None):
    model.eval()
    model.config.use_cache = True
    torch.cuda.reset_peak_memory_stats()
    records = []
    generation_seconds = 0.
    started = time.monotonic()
    outfile.parent.mkdir(parents=True,exist_ok=True)
    eos = model.generation_config.eos_token_id or tokenizer.eos_token_id
    eos = set(eos if isinstance(eos,list) else [eos])
    with outfile.open('w',encoding='utf-8') as f:
        for start in range(0,len(rows),args.eval_batch):
            batch = rows[start:start+args.eval_batch]
            prompts = [tokenizer.apply_chat_template(messages(r,examples),tokenize=False,add_generation_prompt=True) for r in batch]
            tokens = tokenizer(prompts,return_tensors='pt',padding=True,add_special_tokens=False).to('cuda')
            torch.cuda.synchronize()
            batch_start = time.monotonic()
            with torch.inference_mode():
                output = model.generate(**tokens,do_sample=False,max_new_tokens=args.max_new_tokens,
                    pad_token_id=tokenizer.pad_token_id,eos_token_id=list(eos),use_cache=True,
                    repetition_penalty=1.0)
            torch.cuda.synchronize()
            duration = time.monotonic()-batch_start
            generation_seconds += duration
            generated = output[:,tokens['input_ids'].shape[1]:]
            for row, sequence in zip(batch,generated):
                ids = sequence.tolist()
                stop = next((j for j,t in enumerate(ids) if t in eos),len(ids))
                text = tokenizer.decode(ids[:stop],skip_special_tokens=True)
                record = {'id':row['id'],'family':row['family'],'rule_tags':row['rule_tags'],
                    'schema_cluster':row.get('schema_cluster',row['family']),
                    'track':row.get('track','requirements'),
                    'unseen_operator_combination':row.get('unseen_operator_combination',False),
                    'raw_output':text,'output_tokens':min(stop+1,len(ids)),
                    'truncated':stop==len(ids) and len(ids)>=args.max_new_tokens,
                    'batch_seconds':duration,'metrics':score(row,text,suites[row['id']])}
                records.append(record)
                f.write(json.dumps(record,ensure_ascii=False)+'\n')
            f.flush()
            print(json.dumps({'event':'eval_progress','file':str(outfile),'done':len(records),
                              'total':len(rows),'seconds':round(time.monotonic()-started,1)}),flush=True)
            del tokens,output,generated
    summary = aggregate(records)
    summary['seconds'] = time.monotonic()-started
    summary['output_tokens'] = sum(r['output_tokens'] for r in records)
    summary['tokens_per_second'] = summary['output_tokens']/summary['seconds']
    summary['generation_seconds'] = generation_seconds
    summary['generation_tokens_per_second'] = summary['output_tokens']/generation_seconds
    summary['peak_allocated_gb'] = torch.cuda.max_memory_allocated()/1e9
    summary['peak_reserved_gb'] = torch.cuda.max_memory_reserved()/1e9
    outfile.with_suffix('.metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    return summary

def encoded_train(tokenizer,rows,max_length):
    result, lengths = [], []
    for row in rows:
        prompt = tokenizer.apply_chat_template(messages(row),tokenize=True,add_generation_prompt=True)
        full = tokenizer.apply_chat_template(messages(row)+[{'role':'assistant','content':target(row)}],tokenize=True,add_generation_prompt=False)
        if full[:len(prompt)] != prompt:
            raise ValueError('chat template prompt is not an exact prefix')
        if len(full)>max_length:
            raise ValueError(f'{row["id"]}: {len(full)} tokens > {max_length}; do not truncate targets')
        labels = [-100]*len(prompt)+full[len(prompt):]
        result.append((full,labels))
        lengths.append(len(full))
    print(json.dumps({'event':'token_lengths','n':len(rows),'max':max(lengths),
        'p50':float(np.percentile(lengths,50)),'p95':float(np.percentile(lengths,95))}),flush=True)
    return result

def train(model,tokenizer,args,outdir):
    rows = read_rows('train',args.limit)
    data = encoded_train(tokenizer,rows,args.max_length)
    validation = read_rows('validation',args.eval_limit)
    suites = read_suites('validation')
    params = [(n,p) for n,p in model.named_parameters() if p.requires_grad]
    if not params:
        raise ValueError('no trainable parameters')
    expected = 36*(2*2560*args.width+2560+args.width) if args.method=='adapter' else 11796480
    actual = sum(p.numel() for _,p in params)
    if actual!=expected:
        raise ValueError(f'parameter mismatch: {actual} != {expected}')
    frozen = [(n,p) for n,p in model.named_parameters() if not p.requires_grad]
    probes = {n:p.detach().flatten()[::max(1,p.numel()//32)].cpu().clone() for n,p in frozen}
    optimizer = torch.optim.AdamW([p for _,p in params],lr=args.lr,weight_decay=0.01)
    total_steps = math.ceil(len(data)/args.accum)*args.epochs
    scheduler = get_cosine_schedule_with_warmup(optimizer,math.ceil(total_steps*.05),total_steps)
    best, best_epoch, best_key = -1., None, (-1.,-1.,-1.,-1.)
    training_seconds, validation_seconds, peak_gb, step = 0.,0.,0.,0
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    with (outdir/'training.jsonl').open('w',encoding='utf-8') as log:
        for epoch in range(1,args.epochs+1):
            model.train()
            model.config.use_cache=False
            torch.cuda.reset_peak_memory_stats()
            indices=list(range(len(data)))
            random.Random(args.seed+epoch).shuffle(indices)
            optimizer.zero_grad(set_to_none=True)
            started=time.monotonic()
            loss_sum=0.
            for offset,idx in enumerate(indices):
                ids,labels=data[idx]
                ids=torch.tensor([ids],device='cuda')
                labels=torch.tensor([labels],device='cuda')
                # Last accumulation group may contain fewer than accum samples.
                group_size=min(args.accum,len(data)-(offset//args.accum)*args.accum)
                result=model(input_ids=ids,attention_mask=torch.ones_like(ids),labels=labels,use_cache=False)
                if not torch.isfinite(result.loss):
                    raise FloatingPointError('nonfinite loss')
                loss_sum+=float(result.loss.detach())
                (result.loss/group_size).backward()
                if (offset+1)%args.accum==0 or offset+1==len(data):
                    grad=torch.nn.utils.clip_grad_norm_([p for _,p in params],1.0)
                    if not torch.isfinite(grad) or grad<=0:
                        raise FloatingPointError('invalid/zero trainable gradient')
                    optimizer.step(); scheduler.step(); optimizer.zero_grad(set_to_none=True)
                    step+=1
                    event={'epoch':epoch,'step':step,'samples':offset+1,'mean_loss':loss_sum/(offset+1),
                           'grad_norm':float(grad),'lr':scheduler.get_last_lr()[0],
                           'seconds':time.monotonic()-started}
                    log.write(json.dumps(event)+'\n');log.flush()
                    if step%10==0 or offset+1==len(data):
                        print(json.dumps({'event':'train',**event}),flush=True)
                del result,ids,labels
            torch.cuda.synchronize()
            training_seconds+=time.monotonic()-started
            peak_gb=max(peak_gb,torch.cuda.max_memory_allocated()/1e9)
            for n,p in frozen:
                now=p.detach().flatten()[::max(1,p.numel()//32)].cpu()
                if not torch.equal(now,probes[n]):
                    raise RuntimeError('frozen weight changed: '+n)
            metrics=evaluate(model,tokenizer,validation,suites,args,outdir/f'validation_epoch{epoch}.jsonl')
            validation_seconds+=metrics['seconds']
            selection_key=tuple(metrics[k] for k in ['joint_success','data_accuracy','balanced_rule_score','self_consistency'])
            if selection_key>best_key:
                best=metrics['joint_success'];best_epoch=epoch
                best_key=selection_key
                save_trainable(model,outdir/'best.pt')
            save_trainable(model,outdir/'last.pt')
            status={'status':'training' if epoch<args.epochs else 'complete','epoch':epoch,
                    'best_epoch':best_epoch,'best_validation_joint':best,'trainable_parameters':actual,
                    'best_selection_key':list(best_key),
                    'training_seconds':training_seconds,'validation_seconds':validation_seconds,
                    'training_peak_allocated_gb':peak_gb,'frozen_probe_checks_passed':True}
            (outdir/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    return status

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['train','eval'],required=True)
    p.add_argument('--method',choices=['base','adapter','lora'],required=True)
    p.add_argument('--name',required=True)
    p.add_argument('--checkpoint')
    p.add_argument('--split',default='test',choices=['validation','test','challenge'])
    p.add_argument('--width',type=int,default=64)
    p.add_argument('--lr',type=float,default=1e-4)
    p.add_argument('--epochs',type=int,default=3)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--accum',type=int,default=16)
    p.add_argument('--limit',type=int,default=0)
    p.add_argument('--eval-limit',type=int,default=0)
    p.add_argument('--eval-batch',type=int,default=16)
    p.add_argument('--max-length',type=int,default=4096)
    p.add_argument('--max-new-tokens',type=int,default=2048)
    p.add_argument('--few-shot',action='store_true')
    args=p.parse_args()
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed);torch.cuda.manual_seed_all(args.seed)
    torch.set_num_threads(8)
    outdir=ROOT/'runs'/args.name
    outdir.mkdir(parents=True,exist_ok=True)
    if args.mode=='train' and (outdir/'status.json').exists():
        raise ValueError('training output exists; choose a new name to avoid overwriting')
    model,tokenizer,manifest=build(args)
    config={**vars(args),'model_manifest':manifest,'torch':torch.__version__,
            'gpu':torch.cuda.get_device_name(),'system_prompt':SYSTEM,
            'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'scripts').glob('*.py')},
            'trainable_dtypes':sorted({str(p.dtype) for p in model.parameters() if p.requires_grad}),
            'data_manifest':json.loads((ROOT/'data'/'manifest.json').read_text(encoding='utf-8'))}
    (outdir/f'{args.mode}_{args.split}_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'event':'loaded','method':args.method,'trainable':sum(p.numel() for p in model.parameters() if p.requires_grad)}),flush=True)
    if args.mode=='train':
        result=train(model,tokenizer,args,outdir)
    else:
        examples=None
        if args.few_shot:
            # Exactly three predetermined, spaced training examples, no test access.
            examples=read_rows('train',3)
            (outdir/'few_shot_ids.json').write_text(json.dumps([r['id'] for r in examples]),encoding='utf-8')
        result=evaluate(model,tokenizer,read_rows(args.split,args.eval_limit),read_suites(args.split),
                        args,outdir/f'{args.split}.jsonl',examples)
    print(json.dumps({'event':'complete','name':args.name,'result':{k:v for k,v in result.items() if not k.startswith('by_')}}),flush=True)

if __name__=='__main__':
    main()
