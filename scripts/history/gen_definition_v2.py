# -*- coding: utf-8 -*-
"""Generate the updated definition file with strict Chinese-language criteria."""
from pathlib import Path

base = Path(__file__).resolve().parent.parent

html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>方言电影定义 — 严格中国语言标准（2026修订版 v2.1）</title>
<style>
  :root {
    --bg: #f8f9fa; --card: #fff; --text: #1a1a2e; --muted: #6c757d;
    --border: #dee2e6; --accent: #e63946; --accent-bg: #fde8ea;
    --tier1: #2a9d8f; --tier1-bg: #e0f5f2;
    --tier2a: #e29578; --tier2a-bg: #fce8e0;
    --tier2b: #b08968; --tier2b-bg: #f5ebe0;
    --warn: #f77f00; --warn-bg: #fff3cd;
    --info: #118ab2; --info-bg: #e3f2fd;
    --shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Segoe UI","Microsoft YaHei","PingFang SC",sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; font-size: 14px; }
  .container { max-width: 900px; margin: 0 auto; padding: 24px; }
  .header { background: linear-gradient(135deg,#1a1a2e 0%,#0f3460 100%); color: white; padding: 36px 24px; border-radius: 0 0 20px 20px; margin-bottom: 28px; }
  .header h1 { font-size: 24px; margin-bottom: 6px; }
  .header .sub { font-size: 13px; opacity: 0.8; }
  .header .badge-rev { display: inline-block; background: var(--accent); padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; margin-top: 8px; }
  .section { background: var(--card); border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: var(--shadow); }
  .section h2 { font-size: 17px; font-weight: 700; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 2px solid var(--border); }
  .section h3 { font-size: 15px; font-weight: 600; margin: 16px 0 8px; color: var(--info); }
  .callout { border-radius: 8px; padding: 12px 16px; margin: 12px 0; font-size: 13px; }
  .callout-warn { background: var(--warn-bg); border-left: 4px solid var(--warn); }
  .callout-info { background: var(--info-bg); border-left: 4px solid var(--info); }
  .callout-danger { background: var(--accent-bg); border-left: 4px solid var(--accent); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 12px 0; }
  th { background: #f1f3f5; padding: 8px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
  .tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 11px; font-weight: 600; margin: 1px; }
  .tag-include { background: var(--tier1-bg); color: var(--tier1); }
  .tag-exclude { background: var(--accent-bg); color: var(--accent); }
  code { background: #f1f3f5; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
  ul { padding-left: 20px; }
  li { margin-bottom: 4px; }
  .change-log { background: #f0fdf4; border-left: 4px solid #22c55e; padding: 12px 16px; border-radius: 8px; margin: 12px 0; }
  .change-log h4 { margin-bottom: 6px; color: #15803d; }
  .removed { text-decoration: line-through; color: var(--muted); }
  .added { color: var(--tier1); font-weight: 600; }
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <h1>方言电影定义 — 严格中国语言标准</h1>
    <div class="sub">基于学术定义三层框架，研究对象严格限定为中国境内使用的方言/少数民族语言电影</div>
    <span class="badge-rev">2026-08-10 修订版 v2.1</span>
  </div>
</div>
<div class="container">

  <!-- Change Log -->
  <div class="change-log">
    <h4>本次修订要点（v2.1）</h4>
    <ul>
      <li><span class="removed">移除 Tier 1* 间接判定规则</span>（原 <code>has_chinese and len(parts) > 1</code> 条件已删除）——该规则将"含中文标签+多语言"的电影误判为方言片，实际包含大量含英语/日语的中外合拍片</li>
      <li><span class="added">新增汉语方言标签</span>：武汉话、北京话、南京话、青岛话、大连话、常州话、西安话、长沙话、湘潭话、温州话、苏州话等共 50+ 个标签</li>
      <li><span class="added">重新纳入中国少数民族语言</span>：藏语、维吾尔语、蒙古语、哈萨克语、苗语、彝语、壮语、傣语、侗语、瑶语、白语、哈尼语、傈僳语、佤语、拉祜语、纳西语、锡伯语、朝鲜语（中国朝鲜族语言）等——这些语言承载中国境内特定地域文化与民族身份，符合方言电影"地域文化言语形式"的核心定义</li>
      <li><span class="removed">移除外语</span>（英语、日语、韩语、法语、德语、意大利语、西班牙语、俄语等）——这些外国语言不属于中国语言范畴</li>
      <li>方言片数量：<span class="removed">4,050部（旧）</span> → <span class="added">3,487部（v2.1严格）</span>，移除 563 部</li>
    </ul>
  </div>

  <!-- Section 1: Academic Definition -->
  <div class="section">
    <h2>一、学术定义（三层框架）</h2>
    <p>方言电影是指同时满足以下三个层面的电影类型：</p>
    <table>
      <thead><tr><th>层面</th><th>内涵</th></tr></thead>
      <tbody>
        <tr><td><strong>量的维度</strong></td><td>主要人物使用方言/少数民族语言，对白比重达标（可单一或多种语言混用）。方言/少数民族语言是影片声音语言的主体，非点缀性插曲。</td></tr>
        <tr><td><strong>质的维度</strong></td><td>方言/少数民族语言承担叙事功能，参与主题表达和内涵建构。它不是调节节奏或气氛的工具，而是观众理解影片核心意义的审美手段。</td></tr>
        <tr><td><strong>地域特征（核心）</strong></td><td>方言/少数民族语言与地域文化、地域人种、地域自然三位一体，共同建构影片的艺术风格。此为核心界定标准。</td></tr>
      </tbody>
    </table>
    <div class="callout callout-info">
      <strong>排除案例</strong>（《硬汉》）：一个说河南话的外地人只是配角，用来衬托主角性格，不构成方言电影。
    </div>
  </div>

  <!-- Section 2: Scope -->
  <div class="section">
    <h2>二、研究对象范围（严格限定）</h2>
    <div class="callout callout-danger">
      <strong>核心原则</strong>：本研究对象严格限定为<strong>中国境内使用的语言</strong>拍摄的电影，包括两类：（1）汉语各方言（汉语的地域变体）；（2）中国境内少数民族语言。二者均承载中国特定地域文化与民族身份，符合方言电影"地域文化言语形式"的核心定义。
    </div>
    <h3>纳入范围（一）：汉语方言</h3>
    <p>以下十大汉语方言区及其次方言均纳入研究范围：</p>
    <table>
      <thead><tr><th>方言大区</th><th>代表性标签</th><th>地域覆盖</th></tr></thead>
      <tbody>
        <tr><td><strong>粤语</strong></td><td>粤语/粵語/cantonese/广东话/广州话/白话</td><td>广东、广西、中国香港、中国澳门</td></tr>
        <tr><td><strong>闽南语</strong></td><td>闽南语/閩南語/hokkien/福建话/潮州话/潮汕话</td><td>福建南部、广东东部、中国台湾</td></tr>
        <tr><td><strong>吴语</strong></td><td>上海话/shanghainese/沪语/吴语/苏州话/杭州话/温州话</td><td>上海、江苏南部、浙江</td></tr>
        <tr><td><strong>西南官话</strong></td><td>四川话/重庆话/武汉话/贵州话/云南话/西南官话</td><td>四川、重庆、云南、贵州、湖北</td></tr>
        <tr><td><strong>客家话</strong></td><td>客家话/客家話/hakka/客家语</td><td>广东东部、福建西部、江西南部</td></tr>
        <tr><td><strong>湘语</strong></td><td>湘语/湖南话/长沙话/湘潭话/益阳话</td><td>湖南大部</td></tr>
        <tr><td><strong>赣语</strong></td><td>赣语/江西话/鄱阳话</td><td>江西大部</td></tr>
        <tr><td><strong>晋语</strong></td><td>晋语/山西方言/太原话/大同话</td><td>山西、内蒙古中西部</td></tr>
        <tr><td><strong>徽语</strong></td><td>徽语/徽州话</td><td>安徽南部、浙江西北部</td></tr>
        <tr><td><strong>平话</strong></td><td>平话/桂柳话</td><td>广西</td></tr>
      </tbody>
    </table>
    <p>此外，<strong>官话区的地域变体</strong>也纳入研究范围（因其具有鲜明的地域特征）：</p>
    <ul>
      <li><strong>东北官话</strong>：东北话/东北方言/大连话</li>
      <li><strong>胶辽官话</strong>：青岛话/山东话</li>
      <li><strong>中原官话</strong>：河南话/陕西话/西安话</li>
      <li><strong>兰银官话</strong>：甘肃方言/新疆方言</li>
      <li><strong>江淮官话</strong>：南京话/徐州话</li>
      <li><strong>北京官话</strong>：北京话/天津话</li>
      <li><strong>台语</strong>（闽南语中国台湾变体）：台语/臺語/taiwanese</li>
    </ul>

    <h3>纳入范围（二）：中国少数民族语言</h3>
    <p>中国境内各民族使用的语言，承载特定地域文化与民族身份，纳入方言电影研究范围：</p>
    <table>
      <thead><tr><th>语族/语系</th><th>代表性标签</th></tr></thead>
      <tbody>
        <tr><td><strong>藏缅语族</strong></td><td>藏语、彝语、纳西语、哈尼语、傈僳语、拉祜语、白语、土家语、羌语、普米语、怒语、独龙语、阿昌语、基诺语</td></tr>
        <tr><td><strong>壮侗语族</strong></td><td>壮语、傣语、侗语、仫佬语、仡佬语、水语、黎语</td></tr>
        <tr><td><strong>苗瑶语族</strong></td><td>苗语、瑶语</td></tr>
        <tr><td><strong>阿尔泰语系（中国境内）</strong></td><td>维吾尔语、哈萨克语、蒙古语、柯尔克孜语、塔吉克语、乌孜别克语、塔塔尔语、撒拉语、裕固语、东乡语、保安语、达斡尔语、鄂温克语、鄂伦春语、赫哲语、满语、锡伯语、朝鲜语（中国朝鲜族语言）</td></tr>
        <tr><td><strong>南亚语系/南岛语系（中国境内）</strong></td><td>佤语、布朗语、德昂语、京语、高山语</td></tr>
      </tbody>
    </table>
    <div class="callout callout-info">
      <strong>说明</strong>："朝鲜语"在中国语境下指中国朝鲜族语言，与朝鲜半岛国家语言（韩语/韓語/한국어）区分。后者作为外语排除。
    </div>

    <h3>排除范围（非中国语言）</h3>
    <table>
      <thead><tr><th>类别</th><th>示例</th><th>排除理由</th></tr></thead>
      <tbody>
        <tr><td><strong>外语</strong></td><td>英语、日语、韩语（한국어）、法语、德语、意大利语、西班牙语、俄语、泰语、越南语等</td><td>外国语言，非中国语言</td></tr>
        <tr><td><strong>手语</strong></td><td>手语/台湾手语</td><td>视觉-手势语言系统，非口头方言</td></tr>
        <tr><td><strong>戏曲声腔</strong></td><td>京剧、黄梅戏、曲剧</td><td>戏曲声腔，非生活对白方言</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Section 3: Operational Rules -->
  <div class="section">
    <h2>三、操作化判定规则（对应 Is_Dialect 字段）</h2>
    <div class="callout callout-warn">
      <strong>核心变更</strong>：删除了原 <code>has_chinese and len(parts) > 1</code> 间接判定规则。该规则将任何含中文标签且语言字段有多个标签的电影标记为 Is_Dialect=1，导致大量含英语/日语的中外合拍片被误判。现在仅当语言字段<strong>显式包含中国方言或少数民族语言标签</strong>时才判定为方言片。
    </div>
    <h3>决策树</h3>
    <table>
      <thead><tr><th>条件</th><th>Is_Dialect</th><th>层级</th><th>信号强度</th></tr></thead>
      <tbody>
        <tr><td>语言字段<strong>不含</strong>任何中国方言/少数民族语言标签</td><td>0</td><td>非方言</td><td>—</td></tr>
        <tr><td>语言字段<strong>含</strong>中国方言/少数民族语言标签 + <strong>不含</strong>普通话/国语标签</td><td>1</td><td><span class="tag tag-include">Tier 1 纯方言片</span></td><td>强信号</td></tr>
        <tr><td>语言字段<strong>含</strong>中国方言/少数民族语言标签 + <strong>含</strong>普通话标签，且方言排第一</td><td>1</td><td><span class="tag" style="background:var(--tier2a-bg);color:var(--tier2a)">Tier 2a 方言排首位</span></td><td>中信号</td></tr>
        <tr><td>语言字段<strong>含</strong>中国方言/少数民族语言标签 + <strong>含</strong>普通话标签，但普通话排第一</td><td>1</td><td><span class="tag" style="background:var(--tier2b-bg);color:var(--tier2b)">Tier 2b 普通话排首位</span></td><td>弱信号</td></tr>
      </tbody>
    </table>
    <div class="callout callout-info">
      <strong>Tier 1* 已删除</strong>：原 Tier 1*（间接判定，784部）不再计入方言片。这些电影的语言字段不含显式方言标签，仅因"含中文+多语言"规则被触发，实际多为普通话+外语的中外合拍片。
    </div>
  </div>

  <!-- Section 4: Dialect Markers -->
  <div class="section">
    <h2>四、中国语言标签白名单（DIALECT_MARKERS_STRICT）</h2>
    <p>以下标签按语言大区组织，共覆盖 <strong>90+</strong> 个中国方言及少数民族语言标签：</p>
    <table>
      <thead><tr><th>语言大区</th><th>标签列表</th></tr></thead>
      <tbody>
        <tr><td><strong>粤语</strong></td><td>粤语 粵語 cantonese 广东话 廣東話 广州话 廣州話 广西白话 顺德话 白话</td></tr>
        <tr><td><strong>闽南语</strong></td><td>闽南语 閩南語 hokkien 闽南话 閩南話 福建话 福建方言 潮州话 潮州話 潮汕话 潮汕方言 汕尾话 min nan</td></tr>
        <tr><td><strong>吴语</strong></td><td>上海话 shanghainese 沪语 滬語 吴语 吳語 吴越方言 苏州话 蘇州話 杭州话 宁波话 温州话 常州话 上海方言 象山方言</td></tr>
        <tr><td><strong>西南官话</strong></td><td>四川话 四川話 sichuanese 四川方言 重庆话 重慶話 重庆方言 贵州话 贵州方言 贵阳方言 云南话 云南方言 武汉话 武汉方言 西南官话 西南方言 自贡方言</td></tr>
        <tr><td><strong>客家话</strong></td><td>客家话 客家話 hakka 客家语 闽西客家方言</td></tr>
        <tr><td><strong>湘语</strong></td><td>湘语 湘方言 湖南话 湖南話 湖南方言 长沙话 長沙方言 湘潭话 湘潭方言 益阳方言 湘西方言</td></tr>
        <tr><td><strong>赣语</strong></td><td>赣语 贛語 赣方言 江西话 鄱阳方言</td></tr>
        <tr><td><strong>晋语</strong></td><td>晋语 晉語 晋方言 山西方言 山西话 太原话 大同话 大同方言 山西太谷方言</td></tr>
        <tr><td><strong>徽语</strong></td><td>徽语 徽州话 徽州方言</td></tr>
        <tr><td><strong>平话</strong></td><td>平话 平話 桂柳话</td></tr>
        <tr><td><strong>东北/冀鲁/胶辽官话</strong></td><td>东北话 东北方言 东北官话 大连话 青岛话 胶辽官话 山东话 山东方言 唐山话 唐山方言</td></tr>
        <tr><td><strong>中原/兰银官话</strong></td><td>河南话 河南方言 河南周口话 陕西话 陝西話 陕西方言 陕北方言 西安话 甘肃方言 新疆方言 中国陕北方言 西北方言</td></tr>
        <tr><td><strong>江淮官话</strong></td><td>南京话 nankinese 徐州话 蚌埠话 邯郸方言 安徽方言 浙江方言</td></tr>
        <tr><td><strong>北京官话</strong></td><td>北京话 天津话 天津方言</td></tr>
        <tr><td><strong>台语（闽南语台湾变体）</strong></td><td>台语 臺語 taiwanese 台語</td></tr>
        <tr><td><strong>中国少数民族语言</strong></td><td>藏语 维吾尔语 蒙古语 哈萨克语 苗语 彝语 壮语 傣语 侗语 瑶语 白语 哈尼语 傈僳语 佤语 拉祜语 纳西语 锡伯语 朝鲜语 柯尔克孜语 塔吉克语 乌孜别克语 塔塔尔语 撒拉语 裕固语 东乡语 保安语 达斡尔语 鄂温克语 鄂伦春语 赫哲语 满语 土家语 羌语 普米语 怒语 独龙语 阿昌语 基诺语 仫佬语 仡佬语 水语 黎语 布朗语 德昂语 京语 高山语 少数民族语</td></tr>
        <tr><td><strong>通用汉语方言标签</strong></td><td>方言 汉语方言 中文方言 地方方言 广西方言</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Section 5: Known Biases -->
  <div class="section">
    <h2>五、已知偏差与缓解措施</h2>
    <table>
      <thead><tr><th>偏差</th><th>说明</th><th>缓解措施</th></tr></thead>
      <tbody>
        <tr><td>豆瓣标签型限制</td><td>豆瓣"语言"字段标注影片中"出现过"的所有语言，而非主要对白语言占比</td><td>无法完全消除，通过Tier分层和方言排位近似判断</td></tr>
        <tr><td>学术纯方言片被降级</td><td>《秋菊打官司》《小武》等学术纯方言片因豆瓣同时标注了普通话，被归入Tier 2</td><td>Tier 2a（方言排首）作为次优选，仍保留为方言片</td></tr>
        <tr><td>审美意图盲区</td><td>无法从元数据判定方言/少数民族语言是"装饰点缀"还是"叙事核心"</td><td>通过Tier 1（纯方言，强信号）作为最可靠代理</td></tr>
        <tr><td>地域特征代理变量</td><td>方言标签间接携带地域信息，但非直接度量地域文化/人种/自然</td><td>承认这是间接度量，报告中明确标注</td></tr>
        <tr><td>少数民族语言与外语混淆</td><td>部分标签（如朝鲜语 vs 韩语）在豆瓣标注中可能混用</td><td>以"中国境内使用"为原则进行归属判定；中国少数民族语言纳入，外国语言排除</td></tr>
      </tbody>
    </table>
  </div>

  <!-- Section 6: Data Impact -->
  <div class="section">
    <h2>六、修订对数据的影响</h2>
    <table>
      <thead><tr><th>指标</th><th>旧定义</th><th>新定义 v2.1（严格中国语言）</th><th>变化</th></tr></thead>
      <tbody>
        <tr><td>中国电影总数</td><td>11,121</td><td>11,121</td><td>不变</td></tr>
        <tr><td>方言片总数</td><td>4,050</td><td><strong>3,487</strong></td><td style="color:var(--accent)">-563</td></tr>
        <tr><td>Tier 1 纯方言</td><td>2,270</td><td><strong>2,321</strong></td><td style="color:var(--tier1)">+51</td></tr>
        <tr><td>Tier 1* 间接判定</td><td>784</td><td><strong>0（已删除）</strong></td><td style="color:var(--accent)">-784</td></tr>
        <tr><td>Tier 2a 方言排首</td><td>401</td><td><strong>431</strong></td><td style="color:var(--tier1)">+30</td></tr>
        <tr><td>Tier 2b 普通话排首</td><td>595</td><td><strong>735</strong></td><td style="color:var(--tier1)">+140</td></tr>
        <tr><td>普通话/非方言片</td><td>7,071</td><td><strong>7,634</strong></td><td style="color:var(--tier1)">+563</td></tr>
        <tr><td>方言片均分</td><td>6.55</td><td><strong>6.57</strong></td><td>+0.02</td></tr>
        <tr><td>方言片烂片率</td><td>9.7%</td><td><strong>8.5%</strong></td><td style="color:var(--tier1)">-1.2pp</td></tr>
        <tr><td>普通话片均分</td><td>6.16</td><td><strong>6.18</strong></td><td>+0.02</td></tr>
        <tr><td>普通话片烂片率</td><td>23.5%</td><td><strong>23.0%</strong></td><td>-0.5pp</td></tr>
      </tbody>
    </table>
    <div class="callout callout-info">
      <strong>结论</strong>：修订后方言片与普通话片的评分差距<strong>保持稳定</strong>（均分差 0.39，烂片率差 14.5pp），证明方言电影优势结论的稳健性不受定义修订影响。v2.1 定义在严格排除外语的同时，将中国少数民族语言重新纳入，更加符合学术定义中"地域文化言语形式"的核心内涵。
    </div>
  </div>

</div>
</body>
</html>
"""

output_path = base / "方言电影定义_学术标准与操作判定.html"
output_path.write_text(html, encoding="utf-8")
print(f"Definition file updated: {output_path}")
