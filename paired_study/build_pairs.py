"""Build the frozen, template-authored paired requirement study; never runs a model."""
from __future__ import annotations
import copy
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evaluation import DIALECT, validator

SEED = 20261113
OUTPUT = Path(__file__).with_name('pairs.jsonl')
SUFFIX = '所有已声明对象均不得增加其他字段；除明确可选或按条件必填的字段外，其余字段均必填。除上述规则外，不附加取值、长度或数量限制。材料中的具体值只是本次数据，不是固定值规则。请同时给出规则的 JSON Schema（Draft 2020-12，声明 $schema）和整理后的数据，只输出一个含 schema 与 data 两个键的 JSON 对象。'

def obj(props, required=None):
    return {'type':'object', 'properties':props, 'required':list(props) if required is None else required, 'additionalProperties':False}

def root(props, required=None):
    return {'$schema':DIALECT, **obj(props, required)}

def variant(data, **changes):
    return {**copy.deepcopy(data), **changes}

def without(data, key):
    return {k:copy.deepcopy(v) for k,v in data.items() if k != key}

# Each tuple names a distinct recording situation, its exact field names and instance facts.
COUNTS = [
 ('整理社区读书会的借阅包','包名','bundle_name','周末共读','书名列表','books',['山海记','河岸笔记','松林来信']),
 ('登记博物馆导览停靠点','路线名','route_name','古城线','展厅名称列表','halls',['陶器厅','织物厅','木作厅']),
 ('记录咖啡店试饮方案','方案名','plan_name','浅烘对比','豆种名称列表','beans',['云南日晒','埃塞水洗','哥伦比亚蜜处理']),
 ('安排维修站工具包','工具包名','kit_name','单车快修','工具名称列表','tools',['扳手','撬胎棒','打气筒']),
 ('整理小型影展片单','场次名','session_name','城市夜场','影片名称列表','films',['雨巷','归途','夜班']),
 ('登记校园花圃种植批次','批次名','batch_name','秋季补种','植物名称列表','plants',['鼠尾草','金盏菊','三色堇']),
 ('整理餐厅备菜清单','班次名','shift_name','午市','食材名称列表','ingredients',['番茄','豆腐','青椒']),
 ('制作观鸟活动记录','活动名','outing_name','湿地晨行','鸟类名称列表','birds',['白鹭','黑水鸡','夜鹭']),
 ('登记播客后期交接','节目名','podcast_name','旧城声音','音轨名称列表','tracks',['访谈人声','街道环境','片头音乐']),
 ('整理手作课材料袋','课程名','course_name','纸艺入门','材料名称列表','materials',['彩纸','棉线','卡纸']),
 ('录入运动社团训练安排','训练名','training_name','周末基础','动作名称列表','exercises',['深蹲','平板支撑','弓步走']),
 ('登记档案室扫描批次','批次名','scan_name','地方报刊','文件名称列表','files',['六月社论','七月专栏','八月访谈']),
]
OPTIONALS = [
 ('整理民宿预订记录','住客姓名','guest_name','林晓','到店说明','arrival_note','晚间抵达'),
 ('登记图书馆读者资料','读者姓名','reader_name','方宁','联系邮箱','contact_email','fang@example.org'),
 ('整理志愿活动报名','报名人姓名','volunteer_name','沈秋','擅长事项','skill_note','物资整理'),
 ('录入维修委托单','设备名称','device_name','落地灯','故障补充','fault_note','开关偶尔失灵'),
 ('登记画室课程信息','课程名称','class_name','水彩基础','教室提示','room_note','从北门进入'),
 ('整理包裹寄送记录','收件人姓名','recipient_name','唐越','配送备注','delivery_note','放门卫室'),
 ('记录食堂菜单条目','菜名','dish_name','香菇青菜','口味提示','flavor_note','少盐'),
 ('登记音乐排练事项','曲目名称','piece_name','山间小调','演奏说明','performance_note','结尾渐弱'),
 ('整理设备借用申请','借用人姓名','borrower_name','顾晨','用途说明','purpose_note','课程拍摄'),
 ('录入展品目录','展品名称','exhibit_name','青釉碗','来源说明','source_note','居民捐赠'),
 ('登记社区咨询记录','咨询人姓名','visitor_name','孟夏','回访说明','followup_note','周五下午联系'),
 ('整理研讨会发言登记','发言人姓名','speaker_name','周岚','发言备注','talk_note','需要投影'),
]
NULLABLES = [
 ('录入宠物领养记录','动物名字','pet_name','豆豆','健康说明','health_note','已完成检查'),
 ('整理旧书交易条目','书名','book_title','桥边散记','品相说明','condition_note','封面轻微磨损'),
 ('登记旅舍房间资料','房间名称','room_name','南窗房','景观说明','view_note','可见庭院'),
 ('记录录音素材条目','素材名称','clip_name','清晨车站','录制地点','recording_place','东站候车厅'),
 ('整理研究样本台账','样本编号','sample_code','S014','采集说明','collection_note','取自北侧样地'),
 ('登记捐赠物资','物资名称','supply_name','棉被','存放位置','storage_place','二楼西侧'),
 ('整理手工制品订单','制品名称','product_name','木质书签','刻字内容','engraving_text','平安喜乐'),
 ('记录社团成员档案','成员姓名','member_name','陆青','个人简介','bio','喜欢徒步'),
 ('登记会议纪要附件','附件名称','attachment_name','讨论摘要','撰写人姓名','author_name','李禾'),
 ('整理二手乐器信息','乐器名称','instrument_name','中提琴','保养说明','care_note','去年更换琴弦'),
 ('登记口述史访谈','受访者姓名','interviewee_name','陈舟','出生地点','birth_place','临海'),
 ('录入失物招领信息','物品名称','item_name','蓝色雨伞','发现位置','found_place','公交站台'),
]
CONDITIONALS = [
 ('整理工作坊报名','报名类型','enrollment_type',['个人','团体'],'联络说明','contact_note','邮件联系'),
 ('登记配送订单','配送方式','delivery_mode',['快递','自提'],'取送说明','handover_note','下午办理'),
 ('记录设备维修','服务类型','service_type',['上门','送修'],'交接说明','handoff_note','先电话确认'),
 ('整理读书会参加方式','参加方式','attendance_mode',['现场','线上'],'参与说明','participation_note','提前十分钟加入'),
 ('录入展品借展登记','借展方向','loan_direction',['借入','借出'],'保险说明','insurance_note','已有承保文件'),
 ('登记实验室使用申请','使用时段','usage_period',['白天','夜间'],'值守说明','supervision_note','有老师值守'),
 ('整理讲座票务记录','票种','ticket_type',['普通','优惠'],'核验说明','verification_note','现场核对'),
 ('登记摄影作品投稿','投稿类别','submission_type',['单幅','组照'],'作品说明','work_note','城市街景'),
 ('记录食材采购','采购渠道','purchase_channel',['本地','外地'],'验收说明','inspection_note','到货后检查包装'),
 ('整理社区服务申请','申请阶段','request_stage',['首次','续办'],'办理说明','processing_note','柜台核对资料'),
 ('录入活动场地租赁','场地类型','venue_type',['室内','室外'],'布置说明','setup_note','当天完成布置'),
 ('登记数字资料交付','交付形式','delivery_form',['下载','介质'],'交付说明','delivery_note','凭编号领取'),
]

def build():
    rng = random.Random(SEED)
    rows=[]
    def add(family, index, prefix, clauses, facts, schemas, data, probes):
        pair_id=f'{family}_{index+1:02d}'
        # Independent balanced permutations prevent A/B from encoding stricter/looser.
        flip=orientations[family][index]
        order=[1,0] if flip else [0,1]
        for arm, side in zip(('a','b'),order):
            val=validator(schemas[side]); val.validate(data)
            rows.append({'id':f'{pair_id}_{arm}','pair_id':pair_id,'family':family,'arm':arm,
                         'input':prefix+clauses[side]+facts+SUFFIX,
                         'reference_data':copy.deepcopy(data),'reference_schema':schemas[side],
                         'probes':[{'id':pid,'instance':copy.deepcopy(instance),'accept':val.is_valid(instance)} for pid,instance in probes]})
    orientations={}
    for family in ('count_bounds','required_optional','nullable','conditional_dependency'):
        flips=[False]*6+[True]*6; rng.shuffle(flips); orientations[family]=flips
    for i,(scene,label,key,name,list_label,list_key,items) in enumerate(COUNTS):
        # Shift different, overlapping intervals: both directions have a valid witness.
        n=2+(i%3); sample=(items+['补充项目甲','补充项目乙'])[:n]
        data={key:name,list_key:sample}
        schemas=[root({key:{'type':'string'},list_key:{'type':'array','items':{'type':'string'},'minItems':lo,'maxItems':hi}}) for lo,hi in [(n-1,n),(n,n+1)]]
        prefix=f'{scene}。字段：{label}（{key}）为字符串；{list_label}（{list_key}）为字符串数组，保留材料顺序。'
        clauses=[f'{list_key} 的项目数须在 {lo} 至 {hi} 之间（含两端）。' for lo,hi in [(n-1,n),(n,n+1)]]
        facts=f'本次材料：{label}是“{name}”；{list_label}依次是'+ '、'.join('“'+v+'”' for v in sample)+'。'
        probes=[('reference',data),('lower_only',variant(data,**{list_key:sample[:n-1]})),('upper_only',variant(data,**{list_key:sample+["额外名称"]})),('below_both',variant(data,**{list_key:sample[:n-2]})),('above_both',variant(data,**{list_key:sample+["额外甲","额外乙"]})),('other_content',variant(data,**{key:'另一条记录',list_key:['另一个名称']*n})),('wrong_item_type',variant(data,**{list_key:[7]*n})),('missing_list',without(data,list_key)),('extra_field',variant(data,unexpected_field='多余'))]
        add('count_bounds',i,prefix,clauses,facts,schemas,data,probes)
    for family,table in [('required_optional',OPTIONALS),('nullable',NULLABLES)]:
        for i,(scene,label,key,value,tl,tk,tv) in enumerate(table):
            data={key:value,tk:tv}
            prefix=f'{scene}。字段：{label}（{key}）为必填字符串；{tl}（{tk}）记录文本。'
            if family=='required_optional':
                clauses=[f'{tk} 为必填字段，值只能是字符串，不可为 null。',f'{tk} 为可选字段，允许省略；若提供，值只能是字符串，不可为 null。']
                schemas=[root({key:{'type':'string'},tk:{'type':'string'}},req) for req in ([key,tk],[key])]
            else:
                clauses=[f'{tk} 为必填字段，值只能是字符串，不可为 null。',f'{tk} 为必填字段，值可以是字符串或 null。']
                schemas=[root({key:{'type':'string'},tk:{'type':typ}}) for typ in ('string',['string','null'])]
            facts=f'本次材料：{label}是“{value}”，{tl}已知且为“{tv}”。'
            probes=[('reference',data),('target_missing',without(data,tk)),('target_null',variant(data,**{tk:None})),('target_other_text',variant(data,**{tk:'其他说明'})),('target_empty_text',variant(data,**{tk:''})),('target_number',variant(data,**{tk:12})),('target_object',variant(data,**{tk:{}})),('anchor_missing',without(data,key)),('anchor_other_text',variant(data,**{key:'另一条记录'})),('extra_field',variant(data,unexpected_field='多余'))]
            add(family,i,prefix,clauses,facts,schemas,data,probes)
    for i,(scene,dl,dk,states,tl,tk,tv) in enumerate(CONDITIONALS):
        data={dk:states[i%2],tk:tv}
        prefix=f'{scene}。字段：{dl}（{dk}）为必填字符串，只能取“{states[0]}”或“{states[1]}”；{tl}（{tk}）若出现则只能为字符串，不可为 null。'
        clauses=[f'当 {dk} 为“{state}”时，{tk} 必填；当 {dk} 为“{states[1-j]}”时，{tk} 可选、允许省略。' for j,state in enumerate(states)]
        schemas=[]
        for state in states:
            s=root({dk:{'type':'string','enum':states},tk:{'type':'string'}},[dk])
            s['if']={'properties':{dk:{'const':state}},'required':[dk]}
            s['then']={'required':[tk]}
            schemas.append(s)
        facts=f'本次材料：{dl}是“{data[dk]}”；{tl}已提供，为“{tv}”。'
        probes=[('reference',data)]
        for j,state in enumerate(states):
            current=variant(data,**{dk:state})
            probes.extend([(f'state_{j}_present',current),(f'state_{j}_missing',without(current,tk)),(f'state_{j}_null',variant(current,**{tk:None})),(f'state_{j}_other_text',variant(current,**{tk:'另一个说明'}))])
        probes.extend([('discriminator_missing',without(data,dk)),('discriminator_invalid',variant(data,**{dk:'未定义状态'})),('target_wrong_type',variant(data,**{tk:False})),('extra_field',variant(data,unexpected_field='多余'))])
        add('conditional_dependency',i,prefix,clauses,facts,schemas,data,probes)
    rng.shuffle(rows)
    validate(rows)
    return rows

def validate(rows):
    assert len(rows)==96
    assert Counter(r['family'] for r in rows)=={f:24 for f in ('count_bounds','required_optional','nullable','conditional_dependency')}
    assert len({r['id'] for r in rows})==96
    pairs={}
    for r in rows:
        assert set(r)=={'id','pair_id','family','arm','input','reference_data','reference_schema','probes'}
        v=validator(r['reference_schema']); v.validate(r['reference_data'])
        assert len({p['id'] for p in r['probes']})==len(r['probes'])
        assert all(type(p['accept']) is bool and p['accept']==v.is_valid(p['instance']) for p in r['probes'])
        pairs.setdefault(r['pair_id'],[]).append(r)
    assert len(pairs)==48
    for pair in pairs.values():
        assert len(pair)==2 and {r['arm'] for r in pair}=={'a','b'}
        a,b=pair
        assert a['reference_data']==b['reference_data']
        assert [(p['id'],p['instance']) for p in a['probes']]==[(p['id'],p['instance']) for p in b['probes']]
        labels=[(p['accept'],q['accept']) for p,q in zip(a['probes'],b['probes'])]
        assert (True,True) in labels and (False,False) in labels
        assert (True,False) in labels or (False,True) in labels
        if a['family'] in ('count_bounds','conditional_dependency'):
            assert (True,False) in labels and (False,True) in labels

if __name__=='__main__':
    rows=build()
    text=''.join(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n' for row in rows)
    if OUTPUT.exists():
        existing=OUTPUT.read_text(encoding='utf-8')
        if existing != text:
            raise SystemExit('Frozen pairs.jsonl differs from builder. Resolve deliberately; existing file was not overwritten.')
        validate([json.loads(line) for line in existing.splitlines()])
        print('Frozen dataset verified: 48 pairs / 96 arms; 12 pairs per family.')
    else:
        OUTPUT.write_text(text,encoding='utf-8',newline='\n')
        print('Frozen dataset created: 48 pairs / 96 arms; 12 pairs per family.')
