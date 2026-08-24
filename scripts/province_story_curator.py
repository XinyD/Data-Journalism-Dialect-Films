"""Curated province assets and language narrative metadata for story universe previews."""

from __future__ import annotations

# language tag -> province ids (story_universe provinces use these ids)
LANG_TO_PROVINCES: dict[str, list[str]] = {
    "粤语": ["guangdong", "hongkong", "macau"],
    "潮汕话": ["guangdong", "fujian"],
    "闽南语": ["fujian", "taiwan"],
    "台语": ["taiwan", "fujian"],
    "上海话": ["shanghai", "jiangsu", "zhejiang"],
    "吴语": ["shanghai", "jiangsu", "zhejiang"],
    "四川话": ["sichuan", "chongqing"],
    "重庆话": ["chongqing", "sichuan"],
    "贵州话": ["guizhou"],
    "云南话": ["yunnan"],
    "武汉话": ["hubei"],
    "客家话": ["guangdong", "fujian", "jiangxi", "guangxi"],
    "晋语": ["shanxi"],
    "山西话": ["shanxi"],
    "藏语": ["tibet", "qinghai", "sichuan"],
    "维吾尔语": ["xinjiang"],
    "蒙语": ["inner_mongolia"],
    "哈萨克语": ["xinjiang"],
    "东北话": ["liaoning", "jilin", "heilongjiang"],
    "山东话": ["shandong"],
    "河南话": ["henan"],
    "陕西话": ["shaanxi"],
    "湖南话": ["hunan"],
    "湘语": ["hunan"],
    "赣语": ["jiangxi"],
    "南京话": ["jiangsu"],
    "北京话": ["beijing"],
    "天津话": ["tianjin"],
    "唐山话": ["hebei"],
    "河北话": ["hebei"],
    "江淮官话": ["anhui", "jiangsu"],
    "安徽方言": ["anhui"],
    "浙江方言": ["zhejiang"],
    "广州话": ["guangdong"],
    "彝语": ["sichuan", "yunnan"],
    "壮语": ["guangxi"],
    "苗语": ["guizhou", "hunan"],
    "闽南语": ["fujian", "taiwan"],
}

# Source-tag aliases → canonical story-universe names.
# Do NOT alias 台语→闽南语 or 重庆话→四川话: they stay separate narrative entries.
LANG_ALIASES: dict[str, str] = {
    "广州话": "粤语",
    "山西话": "晋语",
}

# Curated languages with no dialect-tag films in the current extract.
# Injected as pending stars (n=0, films=[]). Do not invent film counts.
PENDING_STORY_LANGS: tuple[str, ...] = ("彝语", "壮语", "苗语")

# Academic dual names for the language panel subtitle. Vernacular `name` stays primary.
LANG_SCHOLARSHIP: dict[str, dict] = {
    "粤语": {"academicName": "粤方言", "family": "汉藏语系 · 汉语族 · 粤语", "aliases": ["广州话"]},
    "闽南语": {"academicName": "闽南片", "family": "汉藏语系 · 汉语族 · 闽语", "aliases": []},
    "台语": {"academicName": "闽南语台湾片", "family": "汉藏语系 · 汉语族 · 闽语", "aliases": ["台湾闽南语"]},
    "潮汕话": {"academicName": "闽南语潮汕片", "family": "汉藏语系 · 汉语族 · 闽语", "aliases": []},
    "上海话": {"academicName": "吴语太湖片", "family": "汉藏语系 · 汉语族 · 吴语", "aliases": []},
    "吴语": {"academicName": "吴方言", "family": "汉藏语系 · 汉语族 · 吴语", "aliases": []},
    "四川话": {"academicName": "西南官话成渝片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "重庆话": {"academicName": "西南官话成渝片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": ["巴蜀官话"]},
    "贵州话": {"academicName": "西南官话贵昆片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "云南话": {"academicName": "西南官话滇方言", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "武汉话": {"academicName": "西南官话武天片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "客家话": {"academicName": "客家方言", "family": "汉藏语系 · 汉语族 · 客家话", "aliases": []},
    "晋语": {"academicName": "晋方言", "family": "汉藏语系 · 汉语族 · 晋语", "aliases": ["山西话"]},
    "藏语": {"academicName": "藏语", "family": "汉藏语系 · 藏缅语族 · 藏语支", "aliases": []},
    "维吾尔语": {"academicName": "维吾尔语", "family": "阿尔泰语系 · 突厥语族 · 葛逻禄语支", "aliases": []},
    "蒙语": {"academicName": "蒙古语", "family": "阿尔泰语系 · 蒙古语族", "aliases": []},
    "哈萨克语": {"academicName": "哈萨克语", "family": "阿尔泰语系 · 突厥语族 · 钦察语支", "aliases": []},
    "东北话": {"academicName": "东北官话", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "山东话": {"academicName": "冀鲁/胶辽官话", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "河南话": {"academicName": "中原官话", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "陕西话": {"academicName": "中原官话关中片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "湖南话": {"academicName": "湘语", "family": "汉藏语系 · 汉语族 · 湘语", "aliases": []},
    "赣语": {"academicName": "赣方言", "family": "汉藏语系 · 汉语族 · 赣语", "aliases": []},
    "南京话": {"academicName": "江淮官话洪巢片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "北京话": {"academicName": "北京官话", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "天津话": {"academicName": "冀鲁官话天津小片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "唐山话": {"academicName": "冀鲁官话保唐片", "family": "汉藏语系 · 汉语族 · 官话", "aliases": []},
    "彝语": {"academicName": "彝语", "family": "汉藏语系 · 藏缅语族 · 彝语支", "aliases": []},
    "壮语": {"academicName": "壮语", "family": "壮侗语系 · 壮傣语支", "aliases": []},
    "苗语": {"academicName": "苗语", "family": "苗瑶语系 · 苗语支", "aliases": []},
    "手语": {"academicName": "中国手语 / 地方自然手语", "family": "视觉-手势语言", "aliases": []},
}


def canonical_lang(name: str) -> str:
    return LANG_ALIASES.get(name, name)

LANGUAGE_META: dict[str, dict] = {
    "粤语": {
        "language": "粤语及其城市口语传统",
        "themes": ["城市", "商业", "家庭", "江湖"],
        "folk": ["饮茶", "醒狮", "粤剧"],
        "history": ["港片工业", "南来北往的迁徙与贸易"],
        "stories": "都市身份、兄弟情义、家庭伦理、商业江湖",
    },
    "潮汕话": {
        "language": "潮汕话（闽南语支）",
        "themes": ["家族", "迁徙", "亲情", "乡土"],
        "folk": ["祭祖", "婚嫁礼俗", "饮食与拜神"],
        "history": ["海洋贸易", "侨乡离散与回归"],
        "stories": "家庭、身份、离散、回归",
    },
    "闽南语": {
        "language": "闽南语 / 闽南方言",
        "themes": ["海洋", "漂泊", "信仰", "乡愁"],
        "folk": ["妈祖信仰", "宗族祭祀", "海港生活"],
        "history": ["海上迁徙", "两岸与侨乡网络"],
        "stories": "漂泊、乡愁、信仰与代际冲突",
    },
    "台语": {
        "language": "台语（闽南语台湾变体）",
        "themes": ["家庭", "时代", "底层", "乡愁"],
        "folk": ["夜市", "庙会", "布袋戏"],
        "history": ["台湾新电影", "乡土与现代性"],
        "stories": "代际、城乡、身份与日常尊严",
    },
    "上海话": {
        "language": "上海话（吴语代表）",
        "themes": ["弄堂", "摩登", "变迁", "人情"],
        "folk": ["弄堂生活", "本帮饮食", "地方曲艺"],
        "history": ["开埠与近现代都市史"],
        "stories": "旧城记忆、阶层流动、都市人情",
    },
    "吴语": {
        "language": "吴语（江浙片）",
        "themes": ["江南", "市井", "家族", "细腻"],
        "folk": ["评弹", "园林", "水乡生活"],
        "history": ["江南市镇文化", "近代工商传统"],
        "stories": "人情世故、家族伦理、江南日常",
    },
    "四川话": {
        "language": "四川话与西南官话",
        "themes": ["市井", "幽默", "生活", "烟火"],
        "folk": ["茶馆", "川剧", "市井闲谈"],
        "history": ["移民文化", "盆地市井传统"],
        "stories": "普通人的命运、荒诞与烟火气",
    },
    "重庆话": {
        "language": "重庆话",
        "themes": ["江湖", "码头", "幽默", "湿热"],
        "folk": ["火锅", "山城步道", "川剧变脸"],
        "history": ["开埠码头文化", "三线建设记忆"],
        "stories": "江湖义气、底层生存、城市性格",
    },
    "贵州话": {
        "language": "贵州方言",
        "themes": ["乡土", "时间", "诗意", "边缘"],
        "folk": ["侗族大歌", "苗寨节庆"],
        "history": ["西南山地多民族交汇"],
        "stories": "乡愁、时间、记忆与梦境",
    },
    "云南话": {
        "language": "云南方言",
        "themes": ["边地", "多元", "迁徙", "日常"],
        "folk": ["泼水节", "茶马古道"],
        "history": ["西南边地多民族共生"],
        "stories": "边地身份、文化相遇、生活纹理",
    },
    "武汉话": {
        "language": "武汉话",
        "themes": ["码头", "江湖", "湿热", "底层"],
        "folk": ["过早", "汉剧", "码头文化"],
        "history": ["九省通衢", "近代工业城市"],
        "stories": "犯罪与命运、湿热城市里的小人物",
    },
    "客家话": {
        "language": "客家话",
        "themes": ["迁徙", "坚韧", "家族", "山地"],
        "folk": ["围屋", "山歌", "宗族礼仪"],
        "history": ["多次大迁徙与定居史"],
        "stories": "离乡、扎根、家族延续",
    },
    "晋语": {
        "language": "晋语 / 山西方言",
        "themes": ["乡土", "历史", "家族", "黄土地"],
        "folk": ["晋剧", "窑洞生活", "庙会"],
        "history": ["晋商传统", "北方农耕文明"],
        "stories": "乡土伦理、时代变迁、家族命运",
    },
    "藏语": {
        "language": "藏语",
        "themes": ["高原", "信仰", "土地", "仪式"],
        "folk": ["转经", "节庆", "牧区生活"],
        "history": ["高原文明与现当代变迁"],
        "stories": "信仰、土地、人与自然",
    },
    "维吾尔语": {
        "language": "维吾尔语",
        "themes": ["丝路", "歌舞", "绿洲", "日常"],
        "folk": ["麦西来甫", "市集与饮食", "口头文学"],
        "history": ["丝路绿洲城镇史"],
        "stories": "日常尊严、文化相遇、地方生活",
    },
    "东北话": {
        "language": "东北官话",
        "themes": ["幽默", "工业", "寒冬", "人情"],
        "folk": ["二人转", "冻梨与炕头", "厂矿生活"],
        "history": ["共和国工业记忆", "闯关东"],
        "stories": "小人物喜剧、工业遗存、东北性格",
    },
    "河南话": {
        "language": "河南方言",
        "themes": ["乡土", "出走", "寻找", "普通人"],
        "folk": ["豫剧", "庙会", "中原农耕"],
        "history": ["中原文明腹地", "人口迁徙输出"],
        "stories": "出走与回归、乡土中国、普通人尊严",
    },
    "陕西话": {
        "language": "陕西方言",
        "themes": ["黄土", "历史", "乡土", "厚重"],
        "folk": ["秦腔", "窑洞", "关中饮食"],
        "history": ["周秦汉唐古都层累"],
        "stories": "历史纵深、乡土伦理、时代裂变",
    },
    "湖南话": {
        "language": "湖南方言",
        "themes": ["辛辣", "江湖", "青春", "躁动"],
        "folk": ["湘菜", "花鼓戏"],
        "history": ["湖湘文化", "近代思潮"],
        "stories": "青春、暴力、时代与个体",
    },
    "山东话": {
        "language": "山东方言",
        "themes": ["豪爽", "乡土", "伦理", "传统"],
        "folk": ["胶东秧歌", "孔孟故里礼俗"],
        "history": ["齐鲁文化", "近代开埠"],
        "stories": "乡土伦理、家族、传统与现代",
    },
    "赣语": {
        "language": "赣语",
        "themes": ["山地", "宗族", "日常"],
        "folk": ["采茶戏", "客家与赣语交汇"],
        "history": ["赣鄱农耕与市镇"],
        "stories": "宗族、山地日常、地方记忆",
    },
    "南京话": {
        "language": "南京话（江淮官话）",
        "themes": ["古都", "民国", "市井"],
        "folk": ["秦淮文化", "金陵饮食"],
        "history": ["六朝古都层累", "民国首都记忆"],
        "stories": "历史余绪、都市人情、时代断面",
    },
    "北京话": {
        "language": "北京官话",
        "themes": ["都城", "胡同", "市井", "时代"],
        "folk": ["京剧", "胡同生活", "京味饮食"],
        "history": ["帝都文化", "近现代政治中心"],
        "stories": "都城小人物、时代变迁、京味日常",
    },
    "天津话": {
        "language": "天津话",
        "themes": ["幽默", "码头", "市井"],
        "folk": ["相声", "狗不理与早点"],
        "history": ["近代开埠", "漕运码头"],
        "stories": "市井喜剧、码头江湖、天津性格",
    },
    "彝语": {
        "language": "彝语",
        "themes": ["山地", "火塘", "仪式", "家族"],
        "folk": ["火把节", "口传史诗"],
        "history": ["西南山地民族历史"],
        "stories": "仪式、家族、山地生存",
    },
    "壮语": {
        "language": "壮语",
        "themes": ["山歌", "边地", "日常"],
        "folk": ["三月三", "壮族山歌"],
        "history": ["岭南多民族共生"],
        "stories": "山歌、爱情、地方日常",
    },
    "苗语": {
        "language": "苗语",
        "themes": ["山地", "银饰", "迁徙"],
        "folk": ["芦笙节", "银饰与服饰"],
        "history": ["苗族多次迁徙史"],
        "stories": "山地生活、迁徙记忆、民族尊严",
    },
    "蒙语": {
        "language": "蒙古语",
        "themes": ["草原", "游牧", "信仰"],
        "folk": ["那达慕", "马头琴"],
        "history": ["草原帝国与游牧文明"],
        "stories": "草原、游牧、人与自然",
    },
    "哈萨克语": {
        "language": "哈萨克语",
        "themes": ["草原", "迁徙", "音乐"],
        "folk": ["冬不拉", "游牧节庆"],
        "history": ["西北草原文化"],
        "stories": "游牧生活、音乐与迁徙",
    },
}

DEFAULT_LANGUAGE_META = {
    "language": "",
    "themes": ["乡土", "日常", "人物"],
    "folk": ["地方节庆", "口头传统"],
    "history": ["地方历史待进一步讲述"],
    "stories": "普通人的命运、地方记忆与文化相遇",
}


def language_meta(tag: str) -> dict:
    canon = canonical_lang(tag)
    base = dict(DEFAULT_LANGUAGE_META)
    base["language"] = canon
    if canon in LANGUAGE_META:
        base.update(LANGUAGE_META[canon])
    scholarship = LANG_SCHOLARSHIP.get(canon, {})
    base["academicName"] = scholarship.get("academicName", canon)
    base["family"] = scholarship.get("family", "")
    base["aliases"] = list(scholarship.get("aliases") or [])
    return base


PROVINCES: list[dict] = [
    {"id": "beijing", "name": "北京", "languages": ["北京话", "官话"], "themes": ["都城", "胡同", "时代"],
     "assets": {"culture": ["京味文化", "胡同市井"], "folk": ["京剧", "庙会"], "food": ["炸酱面", "豆汁"],
                "history": ["元明清帝都", "近现代政治中心"], "myth": ["皇城叙事"], "scenery": ["故宫", "颐和园"]},
     "pending": ["更多当代北京普通人故事"]},
    {"id": "tianjin", "name": "天津", "languages": ["天津话", "北京官话"], "themes": ["幽默", "码头", "市井"],
     "assets": {"culture": ["相声文化"], "folk": ["曲艺"], "food": ["狗不理", "煎饼果子"],
                "history": ["近代开埠", "漕运码头"], "scenery": ["海河风貌"]},
     "pending": ["天津方言电影仍偏少"]},
    {"id": "hebei", "name": "河北", "languages": ["唐山话", "冀鲁官话"], "themes": ["乡土", "工业", "平原"],
     "assets": {"culture": ["燕赵文化"], "folk": ["皮影"], "history": ["燕赵故地"], "scenery": ["燕山", "白洋淀"]},
     "pending": ["更多冀东方言叙事"]},
    {"id": "shanxi", "name": "山西", "languages": ["晋语"], "themes": ["黄土", "晋商", "乡土"],
     "assets": {"culture": ["晋商文化"], "folk": ["晋剧"], "food": ["刀削面", "醋文化"],
                "history": ["晋商传统", "古建遗存"], "scenery": ["平遥古城", "云冈石窟"]},
     "pending": ["晋语电影可继续深耕"]},
    {"id": "inner_mongolia", "name": "内蒙古", "languages": ["蒙语", "东北官话"], "themes": ["草原", "游牧", "边疆"],
     "assets": {"culture": ["草原文化"], "folk": ["那达慕"], "history": ["游牧帝国记忆"], "scenery": ["呼伦贝尔草原"]},
     "pending": ["蒙语电影叙事待扩展"]},
    {"id": "liaoning", "name": "辽宁", "languages": ["东北话"], "themes": ["工业", "幽默", "寒冬"],
     "assets": {"culture": ["东北工业文化"], "folk": ["二人转"], "history": ["共和国工业长子"], "scenery": ["辽东半岛"]},
     "pending": []},
    {"id": "jilin", "name": "吉林", "languages": ["东北话"], "themes": ["工业", "边境", "寒冬"],
     "assets": {"culture": ["东北乡土"], "history": ["林海雪原"], "scenery": ["长白山"]},
     "pending": []},
    {"id": "heilongjiang", "name": "黑龙江", "languages": ["东北话"], "themes": ["幽默", "工业", "移民"],
     "assets": {"culture": ["闯关东记忆"], "history": ["北大荒"], "scenery": ["冰雪风光"]},
     "pending": []},
    {"id": "shanghai", "name": "上海", "languages": ["上海话", "吴语"], "themes": ["摩登", "弄堂", "商业"],
     "assets": {"culture": ["海派文化"], "folk": ["弄堂生活"], "food": ["本帮菜", "生煎"],
                "history": ["开埠史", "远东都会"], "scenery": ["外滩", "石库门"]},
     "pending": []},
    {"id": "jiangsu", "name": "江苏", "languages": ["南京话", "吴语"], "themes": ["江南", "古都", "细腻"],
     "assets": {"culture": ["江南文化"], "folk": ["评弹"], "food": ["淮扬菜"], "history": ["六朝古都"], "scenery": ["苏州园林"]},
     "pending": []},
    {"id": "zhejiang", "name": "浙江", "languages": ["吴语", "浙江方言"], "themes": ["江南", "商路", "海洋"],
     "assets": {"culture": ["浙商文化"], "folk": ["越剧"], "food": ["杭帮菜"], "history": ["海上丝路"], "scenery": ["西湖", "海岛"]},
     "pending": []},
    {"id": "anhui", "name": "安徽", "languages": ["江淮官话", "徽语"], "themes": ["乡土", "徽商", "山地"],
     "assets": {"culture": ["徽文化"], "folk": ["黄梅戏"], "history": ["徽商"], "scenery": ["黄山", "古村落"]},
     "pending": ["徽语电影仍稀缺"]},
    {"id": "fujian", "name": "福建", "languages": ["闽南语", "客家话", "潮汕话"], "themes": ["海洋", "侨乡", "信仰"],
     "assets": {"culture": ["闽南文化", "侨乡"], "folk": ["妈祖信仰"], "food": ["闽菜", "沙县小吃"],
                "history": ["海上丝路", "侨乡离散"], "myth": ["妈祖", "海神信仰"], "scenery": ["鼓浪屿", "土楼"]},
     "pending": []},
    {"id": "jiangxi", "name": "江西", "languages": ["赣语", "客家话"], "themes": ["山地", "革命", "宗族"],
     "assets": {"culture": ["赣鄱文化"], "folk": ["采茶戏"], "history": ["红色根据地", "景德镇瓷都"], "scenery": ["庐山", "婺源"]},
     "pending": ["赣语电影待挖掘"]},
    {"id": "shandong", "name": "山东", "languages": ["山东话", "胶辽官话"], "themes": ["豪爽", "乡土", "海洋"],
     "assets": {"culture": ["齐鲁文化"], "folk": ["胶东秧歌"], "food": ["鲁菜"], "history": ["孔孟故里"], "scenery": ["泰山", "黄海"]},
     "pending": []},
    {"id": "henan", "name": "河南", "languages": ["河南话"], "themes": ["中原", "乡土", "出走"],
     "assets": {"culture": ["中原文化"], "folk": ["豫剧"], "food": ["烩面"], "history": ["华夏文明腹地"], "scenery": ["龙门石窟"]},
     "pending": []},
    {"id": "hubei", "name": "湖北", "languages": ["武汉话"], "themes": ["码头", "江湖", "九省通衢"],
     "assets": {"culture": ["楚文化"], "folk": ["汉剧"], "food": ["热干面"], "history": ["长江中游枢纽"], "scenery": ["黄鹤楼", "长江"]},
     "pending": []},
    {"id": "hunan", "name": "湖南", "languages": ["湖南话", "湘语"], "themes": ["辛辣", "江湖", "青春"],
     "assets": {"culture": ["湖湘文化"], "folk": ["花鼓戏"], "food": ["湘菜"], "history": ["近代思潮"], "scenery": ["张家界"]},
     "pending": []},
    {"id": "guangdong", "name": "广东", "languages": ["粤语", "潮汕话", "客家话"], "themes": ["商业", "家族", "海洋"],
     "assets": {"culture": ["岭南文化", "侨乡"], "folk": ["醒狮", "饮茶"], "food": ["早茶", "粤菜"],
                "history": ["海上丝路", "改革开放前沿"], "scenery": ["珠江三角洲"]},
     "pending": []},
    {"id": "guangxi", "name": "广西", "languages": ["壮语", "粤语", "桂柳话"], "themes": ["山歌", "边地", "多元"],
     "assets": {"culture": ["壮族文化"], "folk": ["三月三"], "food": ["螺蛳粉"], "scenery": ["桂林山水"]},
     "pending": ["壮语电影叙事待扩展"]},
    {"id": "hainan", "name": "海南", "languages": ["闽南语", "黎语"], "themes": ["海洋", "热带", "移民"],
     "assets": {"culture": ["海岛文化"], "history": ["海上丝路驿站"], "scenery": ["热带海岸"]},
     "pending": ["海南方言电影仍较少"]},
    {"id": "chongqing", "name": "重庆", "languages": ["重庆话", "四川话"], "themes": ["江湖", "码头", "幽默"],
     "assets": {"culture": ["山城文化"], "folk": ["火锅"], "history": ["开埠码头", "三线建设"], "scenery": ["两江四岸"]},
     "pending": []},
    {"id": "sichuan", "name": "四川", "languages": ["四川话", "藏语", "彝语"], "themes": ["市井", "幽默", "盆地"],
     "assets": {"culture": ["巴蜀文化"], "folk": ["川剧变脸"], "food": ["火锅", "川菜"], "history": ["蜀道", "移民填川"], "scenery": ["九寨沟", "都江堰"]},
     "pending": []},
    {"id": "guizhou", "name": "贵州", "languages": ["贵州话", "苗语"], "themes": ["山地", "多民族", "诗意"],
     "assets": {"culture": ["黔东南文化"], "folk": ["侗族大歌"], "history": ["山地多民族共生"], "scenery": ["黄果树", "苗寨"]},
     "pending": []},
    {"id": "yunnan", "name": "云南", "languages": ["云南话", "彝语", "白语"], "themes": ["边地", "多元", "迁徙"],
     "assets": {"culture": ["西南边地文化"], "folk": ["泼水节"], "history": ["茶马古道"], "scenery": ["香格里拉", "洱海"]},
     "pending": []},
    {"id": "tibet", "name": "西藏", "languages": ["藏语"], "themes": ["高原", "信仰", "土地"],
     "assets": {"culture": ["藏文化"], "folk": ["转经", "藏历节庆"], "history": ["高原文明"], "myth": ["藏传佛教叙事"], "scenery": ["布达拉宫", "高原"]},
     "pending": []},
    {"id": "shaanxi", "name": "陕西", "languages": ["陕西话", "陕北方言"], "themes": ["黄土", "历史", "厚重"],
     "assets": {"culture": ["关中文化"], "folk": ["秦腔"], "food": ["羊肉泡馍"], "history": ["周秦汉唐古都"], "scenery": ["兵马俑", "黄土高原"]},
     "pending": []},
    {"id": "gansu", "name": "甘肃", "languages": ["甘肃方言", "西北方言"], "themes": ["丝路", "边地", "干旱"],
     "assets": {"culture": ["丝路文化"], "history": ["河西走廊"], "scenery": ["敦煌", "戈壁"]},
     "pending": ["甘肃方言电影待挖掘"]},
    {"id": "qinghai", "name": "青海", "languages": ["藏语", "西北方言"], "themes": ["高原", "多民族", "草原"],
     "assets": {"culture": ["高原文化"], "history": ["青藏文明交汇"], "scenery": ["青海湖"]},
     "pending": ["青海方言叙事偏少"]},
    {"id": "ningxia", "name": "宁夏", "languages": ["西北方言"], "themes": ["黄河", "回族", "边地"],
     "assets": {"culture": ["回族文化"], "history": ["黄河灌溉农业"], "scenery": ["西夏王陵"]},
     "pending": ["宁夏方言电影待开发"]},
    {"id": "xinjiang", "name": "新疆", "languages": ["维吾尔语", "哈萨克语"], "themes": ["丝路", "绿洲", "歌舞"],
     "assets": {"culture": ["西域文化"], "folk": ["麦西来甫"], "history": ["丝路绿洲城镇"], "scenery": ["天山", "沙漠绿洲"]},
     "pending": []},
    {"id": "hongkong", "name": "香港", "languages": ["粤语"], "themes": ["城市", "江湖", "商业"],
     "assets": {"culture": ["港片传统"], "history": ["殖民与回归"], "scenery": ["维多利亚港"]},
     "pending": []},
    {"id": "macau", "name": "澳门", "languages": ["粤语"], "themes": ["海洋", "混杂", "日常"],
     "assets": {"culture": ["中葡交汇"], "history": ["开埠贸易"], "scenery": ["历史城区"]},
     "pending": ["澳门方言电影样本较少"]},
    {"id": "taiwan", "name": "台湾", "languages": ["台语", "闽南语"], "themes": ["家庭", "时代", "乡愁"],
     "assets": {"culture": ["台湾新电影传统"], "folk": ["夜市", "庙会"], "history": ["乡土与现代性"], "scenery": ["阿里山", "海岸线"]},
     "pending": []},
]

PROVINCE_BY_ID = {p["id"]: p for p in PROVINCES}

ASSET_CATEGORY_HINT = {
    "culture": "地方文化气质与认同",
    "folk": "民俗仪式与日常礼俗",
    "food": "饮食记忆与市井味道",
    "history": "历史纵深与时代断面",
    "myth": "神话信仰与口头传统",
    "scenery": "地貌景观与空间意象",
}

PROVINCE_COPY: dict[str, dict] = {
    "macau": {
        "intro": "中西交汇的口岸城市，街巷尺度与人情密度，都适合被拍成日常里的戏剧。澳门本土电影样本虽少，但粤语生活肌理同样浓郁。",
        "storyHooks": ["土生葡人家庭", "口岸劳工与赌徒", "旧城区改造", "离散与回归"],
        "assets": {
            "culture": [
                {"title": "中葡交汇", "desc": "葡式瓷砖、天主教节庆与粤语市井并置，形成独特的混杂现代性。"},
                {"title": "博彩之城", "desc": "霓虹与旧街仅隔一条街，浮华与朴素同框。"},
            ],
            "folk": [
                {"title": "妈祖巡游", "desc": "海洋信仰与社区凝聚的年度仪式。"},
                {"title": "土生节庆", "desc": "葡式游行与华人庙会同日发生，是澳门最鲜明的文化切片。"},
            ],
            "food": [
                {"title": "葡挞与猪扒包", "desc": "殖民饮食本土化后，成为城市味觉名片。"},
                {"title": "粥粉面店", "desc": "街坊邻里社交的微型剧场。"},
            ],
            "history": [
                {"title": "开埠贸易", "desc": "从渔村到国际贸易港，再到回归后的微型城邦。"},
                {"title": "历史城区", "desc": "世界文化遗产所凝固的殖民与华人营建史。"},
            ],
            "scenery": [
                {"title": "大三巴牌坊", "desc": "废墟立面成为城市精神地标。"},
                {"title": "氹仔旧巷", "desc": "窄巷、骑楼与海风，适合拍离散与重逢。"},
            ],
        },
        "pending": [
            "澳门本土方言电影样本仍较少",
            "当前片单多为粤语共片，尚待更多澳门在地叙事",
        ],
    },
    "hongkong": {
        "intro": "高密度都市里藏着江湖、家庭与商业伦理。港片传统让粤语电影拥有全球最成熟的类型语法之一。",
        "storyHooks": ["警匪对峙", "底层合租屋", "移民家庭", "金融时代的人性"],
        "assets": {
            "culture": [
                {"title": "港片传统", "desc": "黑帮、警匪、喜剧与文艺片并行，类型高度成熟。"},
                {"title": "都市密度", "desc": "电梯、茶餐厅、天台——空间越小，戏剧越满。"},
            ],
            "history": [
                {"title": "殖民与回归", "desc": "身份焦虑与本土认同是几代港片的母题。"},
                {"title": "移民潮", "desc": "南下打工、家族团聚与阶层流动。"},
            ],
            "scenery": [
                {"title": "维多利亚港", "desc": "霓虹天际线象征繁华，也反衬底层。"},
                {"title": "重庆大厦", "desc": "全球化微型社会的经典空间。"},
            ],
        },
    },
    "guangdong": {
        "intro": "岭南是中国方言电影产量最丰厚的地区之一：粤语、潮汕话、客家话在此交错，商业、家族与海洋叙事并存。",
        "storyHooks": ["早茶桌上的家族", "侨乡离散", "城中村变迁", "潮汕宗族"],
        "assets": {
            "culture": [
                {"title": "岭南文化", "desc": "务实、市井与海洋性格并重，是粤语片商业伦理与家庭伦理的底色。"},
                {"title": "侨乡", "desc": "出洋、汇款与回乡盖楼，构成代际离散的经典情节骨架。"},
            ],
            "folk": [
                {"title": "醒狮", "desc": "节庆与武馆传统进入电影，常作为社区认同的视觉符号。"},
                {"title": "饮茶", "desc": "早茶桌是谈生意、议婚事、摊开家族矛盾的固定场景。"},
            ],
            "food": [
                {"title": "早茶", "desc": "点心与一盅两件，是粤语日常戏最稳的空间锚点。"},
                {"title": "粤菜", "desc": "鲜味与时令，常被用来写城市生活的体面与压力。"},
            ],
            "history": [
                {"title": "海上丝路", "desc": "口岸贸易把广东写成出入口，而不是封闭的乡土。"},
                {"title": "改革开放前沿", "desc": "特区、民工与暴富神话，是当代粤语片的时代背景。"},
            ],
            "scenery": [
                {"title": "珠江三角洲", "desc": "厂区、城中村与河涌并置，适合拍流动人口的命运。"},
            ],
        },
    },
    "sichuan": {
        "intro": "盆地市井孕育了中国最具幽默感的方言电影传统之一——普通人如何在荒诞里守住尊严。",
        "storyHooks": ["茶馆里的江湖", "移民填川", "小镇青年", "多民族边地"],
        "assets": {
            "culture": [
                {"title": "巴蜀文化", "desc": "茶馆闲谈与市井幽默，让四川话电影擅长写小人物的体面。"},
            ],
            "folk": [
                {"title": "川剧变脸", "desc": "戏曲绝活常被借用为身份、伪装与江湖的隐喻。"},
            ],
            "food": [
                {"title": "火锅", "desc": "围桌喧哗是盆地社交的基本单位，也是群戏的天然舞台。"},
                {"title": "川菜", "desc": "麻辣与市井烟火，用来写生活的热度和荒诞。"},
            ],
            "history": [
                {"title": "蜀道", "desc": "封闭与连通并存，盆地既是避世之所，也是迁徙走廊。"},
                {"title": "移民填川", "desc": "湖广填四川的层累移民，解释了方言混杂与家庭故事的来路。"},
            ],
            "scenery": [
                {"title": "九寨沟", "desc": "川西高原与藏地接壤，是多民族边地叙事的出口。"},
                {"title": "都江堰", "desc": "治水传统把人与土地的关系写成可拍的文明记忆。"},
            ],
        },
    },
    "fujian": {
        "intro": "面向海洋的省份：闽南语、客家话与潮汕话在此相遇，妈祖、土楼与侨乡网络构成独特叙事资源。",
        "storyHooks": ["出洋打工", "宗族祭祀", "海岛日常", "两岸乡愁"],
        "assets": {
            "culture": [
                {"title": "闽南文化", "desc": "宗族、信仰与海洋迁徙缠在一起，是闽南语电影的核心母题。"},
                {"title": "侨乡", "desc": "出洋与汇款改写家庭权力，离散成为日常而不是例外。"},
            ],
            "folk": [
                {"title": "妈祖信仰", "desc": "海神庇护把风险、告别与归乡收进仪式里。"},
            ],
            "food": [
                {"title": "闽菜", "desc": "海鲜与红糟，是港口城市味觉上的地方身份。"},
            ],
            "history": [
                {"title": "海上丝路", "desc": "从刺桐港到当代侨汇，福建的故事总是向外走。"},
                {"title": "侨乡离散", "desc": "南洋网络让一部家庭片也能写成跨国史。"},
            ],
            "myth": [
                {"title": "妈祖", "desc": "护航与招魂的传说，仍在渔村和城市庙宇里并行。"},
            ],
            "scenery": [
                {"title": "鼓浪屿", "desc": "租界遗存与钢琴、海风，适合拍阶层与乡愁。"},
                {"title": "土楼", "desc": "客家聚居的建筑本身就是宗族叙事的布景。"},
            ],
        },
    },
    "guangxi": {
        "intro": "山歌、边地与多民族共生：壮语叙事资源丰厚，但电影样本仍明显不足。",
        "storyHooks": ["三月三歌圩", "边关小镇", "刘三姐传说的当代回声", "粤语与壮语交错的家庭"],
        "assets": {
            "culture": [
                {"title": "壮族文化", "desc": "山歌与日常劳作相连，语言本身就是社交和求偶的媒介。"},
            ],
            "folk": [
                {"title": "三月三", "desc": "歌圩把爱情、节庆与地方认同叠在同一天。"},
            ],
            "food": [
                {"title": "螺蛳粉", "desc": "城市小吃工业把地方味道送出省，也改变了本地自我想象。"},
            ],
            "scenery": [
                {"title": "桂林山水", "desc": "被观光写滥的山水，仍可用来拍边地生活的真实尺度。"},
            ],
        },
    },
    "guizhou": {
        "intro": "山地与多民族交汇处，时间感被拉长：苗寨、侗歌与公路电影共享一种诗意的边缘位置。",
        "storyHooks": ["苗寨少年", "公路与山路", "侗族大歌", "被遗忘的时间"],
        "assets": {
            "culture": [
                {"title": "黔东南文化", "desc": "苗、侗等民族的聚落结构，提供与平原官话完全不同的叙事节奏。"},
            ],
            "folk": [
                {"title": "侗族大歌", "desc": "多声部无伴奏合唱，是共同体记忆的声音形式。"},
            ],
            "history": [
                {"title": "山地多民族共生", "desc": "迁徙与杂居写成的地方史，适合拍相遇而不是征服。"},
            ],
            "scenery": [
                {"title": "黄果树", "desc": "瀑布与喀斯特是观光符号，也可作角色命运的转场。"},
                {"title": "苗寨", "desc": "吊脚楼与银饰把日常生活摆上可拍摄的表面。"},
            ],
        },
    },
    "shanghai": {
        "intro": "开埠百年塑造的海派都市：弄堂、摩登与阶层流动，是上海话电影最擅长的题材。",
        "storyHooks": ["石库门家庭", "租界往事", "弄堂拆迁", "都市男女"],
    },
    "beijing": {
        "intro": "帝都叙事从来不缺厚度：胡同市井与政治中心并置，让小人物故事也有大时代背景。",
        "storyHooks": ["胡同拆迁", "北漂青年", "京剧世家", "大院记忆"],
    },
    "taiwan": {
        "intro": "台湾新电影传统让台语片既有乡土质感，也有现代性的细腻凝视。",
        "storyHooks": ["代际冲突", "乡村教会", "都市孤独", "历史伤痕"],
    },
    "yunnan": {
        "intro": "西南边地是中国叙事资源最丰富的省份之一：多民族、茶马古道与边贸日常交织。",
        "storyHooks": ["边贸小镇", "民族节庆", "生态迁徙", "异域相遇"],
        "assets": {
            "culture": [
                {"title": "西南边地文化", "desc": "彝、白、傣等语言与云南话并存，边地不是背景板，而是叙事主体。"},
            ],
            "folk": [
                {"title": "泼水节", "desc": "节庆把水源、祝福与族群边界变成可拍摄的公共场面。"},
            ],
            "history": [
                {"title": "茶马古道", "desc": "商路把云南写成连接藏地与东南亚的走廊，而不是封闭边疆。"},
            ],
            "scenery": [
                {"title": "香格里拉", "desc": "被旅游命名的地方，仍可用来拍高原上的信仰与生计。"},
                {"title": "洱海", "desc": "湖岸聚落适合写日常，而不是只写风景。"},
            ],
        },
    },
    "xinjiang": {
        "intro": "丝路绿洲与草原文明交汇，歌舞、信仰与日常尊严都是尚未被充分讲述的故事矿脉。",
        "storyHooks": ["绿洲市集", "草原迁徙", "多语家庭", "丝路记忆"],
        "assets": {
            "culture": [
                {"title": "西域文化", "desc": "维吾尔、哈萨克等语言把丝路写成活着的日常，而不是博物馆。"},
            ],
            "folk": [
                {"title": "麦西来甫", "desc": "歌舞集会是社交、节庆与共同体记忆的现场。"},
            ],
            "history": [
                {"title": "丝路绿洲城镇", "desc": "绿洲城市靠水利与贸易存活，适合拍迁徙与驻留。"},
            ],
            "scenery": [
                {"title": "天山", "desc": "山脉分割草原与绿洲，也分割不同的生计方式。"},
                {"title": "沙漠绿洲", "desc": "水源决定聚落，空间本身就会把戏剧推向前。"},
            ],
        },
    },
    "tibet": {
        "intro": "高原空间里，信仰、土地与仪式构成独特的电影语法，藏语片已证明其艺术高度。",
        "storyHooks": ["转经路上的少年", "牧区家庭", "信仰与世俗", "高原生态"],
        "assets": {
            "culture": [
                {"title": "藏文化", "desc": "仪式、家族与土地伦理缠在一起，语言节奏本身就有电影性。"},
            ],
            "folk": [
                {"title": "转经", "desc": "环绕与重复把信仰写成身体动作，而不是解说词。"},
                {"title": "藏历节庆", "desc": "节庆把牧区时间从生产里暂时拉开。"},
            ],
            "history": [
                {"title": "高原文明", "desc": "当代变迁与长时段信仰叠在同一空间里。"},
            ],
            "myth": [
                {"title": "藏传佛教叙事", "desc": "转世、护法与地方神祇，是许多藏语片不必发明的神话层。"},
            ],
            "scenery": [
                {"title": "布达拉宫", "desc": "地标会被观光吞掉，但作为信仰空间仍可拍人如何走近它。"},
                {"title": "高原", "desc": "海拔改变呼吸、行走与戏剧节奏。"},
            ],
        },
    },
}


def _asset_item(title: str, category: str, desc: str | None = None) -> dict:
    # Handwritten desc only. Empty is better than a formulaic "与{title}相关的…" template.
    return {"title": title, "desc": desc or ""}


def normalize_assets(assets: dict) -> dict:
    normalized: dict[str, list] = {}
    for key, items in (assets or {}).items():
        row = []
        for item in items:
            if isinstance(item, dict):
                row.append({"title": item["title"], "desc": item.get("desc", "")})
            else:
                row.append(_asset_item(str(item), key))
        normalized[key] = row
    return normalized


def enrich_province(base: dict) -> dict:
    pid = base["id"]
    name = base["name"]
    themes = base.get("themes") or []
    custom = PROVINCE_COPY.get(pid, {})
    intro = custom.get(
        "intro",
        f"{name}的故事，藏在{'、'.join(themes[:3]) if themes else '日常'}之中——地方语言、风俗与历史，都是尚未被充分讲述的叙事资源。",
    )
    story_hooks = custom.get(
        "storyHooks",
        [f"{t}叙事" for t in themes[:3]] + ["普通人命运", "代际与离散"],
    )
    assets = normalize_assets(custom.get("assets") or base.get("assets", {}))
    pending = custom.get("pending", base.get("pending", []))
    languages = []
    seen_langs = set()
    for name in base.get("languages") or []:
        canon = canonical_lang(name)
        if canon in seen_langs:
            continue
        seen_langs.add(canon)
        languages.append(canon)
    return {
        **base,
        "languages": languages,
        "intro": intro,
        "storyHooks": story_hooks[:4],
        "assets": assets,
        "pending": pending,
    }


def get_provinces() -> list[dict]:
    return [enrich_province(p) for p in PROVINCES]

