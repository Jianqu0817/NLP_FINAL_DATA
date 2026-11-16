"""Build frozen confirmation probes; no model/service calls. Existing differences abort."""
import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
DIALECT = 'https://json-schema.org/draft/2020-12/schema'
COMMON = [
 '所有字段均必填，所有对象都不允许增加其他字段。',
 '除已说明的规则外，不增加取值、长度或数量限制；材料值不表示固定值规则。',
 '请同时给出规则的 JSON Schema（Draft 2020-12，声明 $schema）和整理后的数据，只输出一个含 schema 与 data 两个键的 JSON 对象。'
]
ALT_COMMON = [
 '每个字段都必须出现，各对象不得含未声明的字段。',
 '没有另行说明的取值、长度和数量一律不设限制；本次材料的值不需要固定为规则。',
 '输出仅为一个具有 schema、data 两个键的 JSON 对象：schema 写明 Draft 2020-12 的 $schema 并表示规则，data 是整理后的材料。'
]
# All named tasks and field keys differ from the previous paired study.
COUNTS = [
 ('编制天文台夜间观测清单','night_code','target_stars','calibration_lamps','夜巡甲','天狼星|织女星|牛郎星|北极星','氖灯|氩灯'),
 ('整理古籍字形比对单','folio_code','glyph_forms','ink_traces','字页乙','篆体甲|隶体乙|楷体丙|行体丁','浓墨|淡墨'),
 ('记录港口浮标巡检','buoy_sector','marker_codes','wave_notes','东锚区','浮标甲|浮标乙|浮标丙|浮标丁','微浪|涌浪'),
 ('编写剧场灯光预置','cue_label','beam_presets','gel_codes','序幕蓝','顶光|侧光|逆光|面光','蓝片|琥珀片'),
 ('整理地层剖面调查','section_code','stratum_names','fossil_marks','北壁段','砂层|泥层|砾层|灰层','螺印|叶印'),
 ('登记风筝试飞方案','flight_code','sail_shapes','tether_colors','春风甲','燕形|蝶形|鹰形|鱼形','红绳|白绳'),
 ('编排陶窑装烧位置','kiln_code','shelf_slots','glaze_shades','窑次丙','上层东|中层东|下层东|底层东','青釉|白釉'),
 ('记录冰川测量断面','transect_code','stake_labels','snow_textures','冰舌西','桩甲|桩乙|桩丙|桩丁','粉雪|粒雪'),
 ('安排灯塔透镜校准','beacon_code','lens_segments','test_colors','岬角灯','镜段甲|镜段乙|镜段丙|镜段丁','红光|绿光'),
 ('整理织机经线配置','loom_code','warp_groups','shuttle_marks','织位戊','经组甲|经组乙|经组丙|经组丁','梭记甲|梭记乙'),
 ('登记矿洞通风检查','shaft_code','vent_nodes','dust_colors','井巷南','风点甲|风点乙|风点丙|风点丁','灰尘|褐尘'),
 ('编写木偶舞台调度','act_code','puppet_roles','curtain_patterns','水榭折','渔翁|书生|童子|船娘','波纹|云纹'),
 ('记录盐田结晶观察','pan_code','crystal_sites','brine_hues','盐畦六','晶点甲|晶点乙|晶点丙|晶点丁','浅黄|无色'),
 ('整理声学消声测试','chamber_code','baffle_units','tone_labels','静室辛','隔板甲|隔板乙|隔板丙|隔板丁','低音|高音'),
 ('安排城市日晷校时','dial_code','shadow_marks','sky_states','晷面午','影标甲|影标乙|影标丙|影标丁','晴空|薄云'),
 ('编写潜水礁盘勘察','reef_code','coral_patches','current_signs','礁区壬','珊区甲|珊区乙|珊区丙|珊区丁','顺流|回流'),
]
NULLS = [
 ('登记酿醋坛封存信息','vat_code','aroma_record','seal_record','醋坛甲','酸香清楚','蜡封完整'),
 ('记录钟表摆轮检测','caliber_code','balance_record','spring_record','机芯乙','摆幅稳定','游丝平整'),
 ('整理洞穴壁画观察','grotto_code','pigment_record','crack_record','洞室丙','赭色明显','裂隙细小'),
 ('登记水闸启闭核验','sluice_code','hinge_record','gauge_record','闸口丁','转轴顺畅','水尺清晰'),
 ('记录蜡染纹样修复','dye_code','wax_record','fiber_record','染幅戊','蜡线连续','纤维牢固'),
 ('编制气球探空日志','balloon_code','ascent_record','radio_record','探空气球己','上升均匀','信号稳定'),
 ('登记砚台石质观察','inkstone_code','grain_record','rim_record','砚台庚','石纹细密','边沿平整'),
 ('记录雪橇滑板检查','sled_code','runner_record','lash_record','雪橇辛','滑面平直','绑带紧实'),
]

def schema(props):
 return {'$schema':DIALECT,'type':'object','properties':props,'required':list(props),'additionalProperties':False}

def with_value(data,key,value):
 x=copy.deepcopy(data); x[key]=value; return x

def finish(pairid,family,arm,task,fields,rule,facts,altfields,altrule,altfacts,ref,rs,instances,meta):
 sentences=[task+'。',fields,rule,facts]+COMMON
 alternate=[task+'。',altfields,altrule,altfacts]+ALT_COMMON
 # Same exact sentences, only the four middle semantic blocks are permuted.
 order=[sentences[i] for i in [0,3,2,1,4,5,6]]
 core={'id':pairid+'_'+arm,'pair_id':pairid,'family':family,'arm':arm,
       'reference_data':ref,'reference_schema':rs,'probes':[],**meta}
 Draft202012Validator.check_schema(rs)
 v=Draft202012Validator(rs);v.validate(ref)
 core['probes']=[{'id':k,'instance':x,'accept':v.is_valid(x)} for k,x in instances]
 out=[]
 for variant,ss in [('original',sentences),('wording',alternate),('order',order)]:
  out.append(dict(core,variant=variant,input=''.join(ss),input_sentences=ss))
 return out

def build():
 variants={k:[] for k in ['original','wording','order']}
 for i,(task,anchor,focus,decoy,name,vs,ds) in enumerate(COUNTS,1):
  bounds=[(2,4),(1,3)] if i%4 in (1,2) else [(3,5),(2,4)]
  if i%2==0: bounds.reverse()
  n=max(x[0] for x in bounds); vals=vs.split('|')[:n]; decoys=ds.split('|')
  keys=[focus,decoy] if i%2 else [decoy,focus]
  ref={anchor:name,**{k:vals if k==focus else decoys for k in keys}}
  fields=f'字段：{anchor} 是字符串；'+ '；'.join(f'{k} 是字符串数组，保留材料顺序' for k in keys)+'。'
  altfields=f'使用字符串字段 {anchor}；'+ '；'.join(f'用字符串数组 {k} 按材料顺序记录' for k in keys)+'。'
  facts=f'本次材料：{anchor} 为“{name}”；'+'；'.join(f'{k} 依次为'+ '、'.join('“'+x+'”' for x in ref[k]) for k in keys)+'。'
  altfacts=f'此次提供：{anchor} 的内容是“{name}”；'+'；'.join(f'{k} 的有序内容是'+ '、'.join('“'+x+'”' for x in ref[k]) for k in keys)+'。'
  inst=[('reference',ref)]+[(f'focus_n_{n}',with_value(ref,focus,['另一项']*n)) for n in range(7)]
  inst += [(f'distractor_n_{n}',with_value(ref,decoy,['旁项']*n)) for n in [0,6]]
  inst += [('wrong_item_type',with_value(ref,focus,[17]*n)),('missing_focus',{k:v for k,v in ref.items() if k!=focus}),('extra_field',dict(ref,confirm_extra='多余')),('other_content',{anchor:'另一编号',**{k:['替换']*len(ref[k]) for k in keys}})]
  for arm,(lo,hi) in zip('ab',bounds):
   props={anchor:{'type':'string'},**{k:{'type':'array','items':{'type':'string'},**({'minItems':lo,'maxItems':hi} if k==focus else {})} for k in keys}}
   rows=finish(f'confirm_count_{i:02d}','count_bounds',arm,task,fields,f'{focus} 的项目数须在 {lo} 至 {hi} 之间（含两端）。',facts,altfields,f'{focus} 至少包含 {lo} 项且至多包含 {hi} 项。',altfacts,ref,schema(props),inst,{'focus_field':focus,'distractor_field':decoy,'expected_min':lo,'expected_max':hi,'expected_nullable':False})
   for r in rows: variants[r['variant']].append(r)
 for i,(task,anchor,focus,decoy,name,fv,dv) in enumerate(NULLS,1):
  decoy_null=i%2==0
  keys=[focus,decoy] if i%2 else [decoy,focus]
  ref={anchor:name,**{k:fv if k==focus else dv for k in keys}}
  fields=f'字段：{anchor} 为字符串；'+ '；'.join(f'{k} 记录文本' for k in keys)+f'；{decoy} 的值'+('允许是字符串或 null' if decoy_null else '只允许是字符串，不允许 null')+'。'
  altfields=f'用字符串 {anchor} 记录编号；'+'；'.join(f'用 {k} 保存文字' for k in keys)+f'；{decoy} '+('可填写字符串，也可填写 null' if decoy_null else '必须填写字符串，不能填写 null')+'。'
  facts=f'本次材料：{anchor} 是“{name}”；'+'；'.join(f'{k} 已知且为“{ref[k]}”' for k in keys)+'。'
  altfacts=f'此次提供：{anchor} 的内容为“{name}”；'+'；'.join(f'{k} 的已知文本是“{ref[k]}”' for k in keys)+'。'
  inst=[('reference',ref),('target_null',with_value(ref,focus,None)),('target_missing',{k:v for k,v in ref.items() if k!=focus}),('target_other_text',with_value(ref,focus,'另一说明')),('target_empty_text',with_value(ref,focus,'')),('target_number',with_value(ref,focus,17)),('target_object',with_value(ref,focus,{})),('distractor_null',with_value(ref,decoy,None)),('anchor_missing',{k:v for k,v in ref.items() if k!=anchor}),('extra_field',dict(ref,confirm_extra='多余'))]
  for arm,nullable in zip('ab',[False,True] if i%2 else [True,False]):
   props={anchor:{'type':'string'},**{k:{'type':['string','null'] if (nullable if k==focus else decoy_null) else 'string'} for k in keys}}
   rule=f'{focus} 的值'+('允许是字符串或 null。' if nullable else '只允许是字符串，不允许 null。')
   altrule=f'{focus} '+('可填写字符串，也可填写 null。' if nullable else '必须填写字符串，不能填写 null。')
   rows=finish(f'confirm_nullable_{i:02d}','nullable',arm,task,fields,rule,facts,altfields,altrule,altfacts,ref,schema(props),inst,{'focus_field':focus,'distractor_field':decoy,'expected_min':None,'expected_max':None,'expected_nullable':nullable})
   for r in rows: variants[r['variant']].append(r)
 return variants

def main():
 for variant,rows in build().items():
  content=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows)
  path=HERE/f'confirm_{variant}.jsonl'
  if path.exists():
   if path.read_text(encoding='utf-8')!=content: raise ValueError(f'frozen file differs: {path}')
  else: path.write_text(content,encoding='utf-8')
 print('Frozen NEW: 24 pairs / 48 rows in each of three variants.')
if __name__=='__main__':main()
