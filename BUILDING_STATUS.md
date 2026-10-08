# LSEmap模型状态

当前本地完整模型为188版：result/blender/LSE_campus_detailed_v188.blend。6483个对象。原生重开与12项网页检查通过，已部署并核对线上资源及实际页面。

原生SHA256：d923d7bbccad0fdf8600aaa5240d9b3b02cee403baac9ff2265fd8549579b427。

187版按已建正面照片补回MAR底座中间偏右的第三组高窗及混凝土围边，保留两侧原高窗、另一侧开放柱廊及内部几何。照片注册、围边和窗洞尺寸为估算；完整体量仍未核实。

186版修正SAR的4组首层临街窗：保留玻璃几何、UV与拱形窗框，改为中性透光玻璃，并加入照片可见的浅色竖向百叶。80片百叶及窗后暗面仅表达窗部构造；尺度、覆盖范围和光学参数估算，不代表完整房间。

185版将OLD入口两侧楼名字样及校徽下校训重新注册到现有石墙；楼名按石柱宽度适配，字形背面贴合石材。保留可编辑文字、字体、颜色和全部立面网格，字样尺度及间隙为建模估计。

184版将SAL的154段独立山花压顶合为7条连续闭合石带，移除294个内部端盖；7组交叠玻璃退入原窗洞，并补出中央三联窗后的真实砖墙开口；压顶路径、窗洞轮廓、玻璃材质及UV保留。截面及退入深度估算，非现状测绘。

183版按两张已建照片修正SAL主立面6组砖材为暖橙褐色，独立材质保留砖缝与尺度，几何、UV、窗框、玻璃和石材不变。色值估计，照片日期未知，未覆盖的背面与侧面代理保留。

182版按2011年门厅实拍将长凳金属支脚改为连续石材台座，座板、地面和入口位置保留，台座退让尺寸为估计。现状布局仍未完整核验。

181版统一修正28栋楼的玻璃表面策略：3238个朝内闭合组件改为朝外，3863个闭合组件登记为单侧渲染。原颜色、透明度、顶点及逐角UV保留。单层玻璃仍可从两侧查看。该修正不代表重新核验建筑外形、照片日期或完整内部。

所有建筑完整外观、当前内部结构和每个房间尚未完成。可加载模型、局部修正和核对记录均不代表整栋实测完成。照片拍摄日期未知时不称2026实拍。

## MAR北立面修正依据与范围

187版原生模型核对发现：北立面上部开口横向位置与Nick Kane已建正面照片02不符。以两侧已存在的底座高窗作水平参照，照片开口估算对应局部X为-4.92至8.17；模型在25.2、28.1、31.1三个高度的前窗墙空缺均为-15.00至-2.25，中心约偏移10.25m。该数字依赖当前模型比例及照片取点，含透视和进深视差，不是现场测量。

下一步须联合核对两侧窗墙、开口侧壁、后方楼翼与退台，不能只平移表面玻璃。当前187版尚未修复此项。复核脚本为web/tools/audit_mar_north_alignment.py，原生射线和照片注册记录在result/blender/mar-north-alignment/alignment.json。核对没有修改模型或线上资产，也未新增整模备份。

MAR188独立候选已同步重建北立面上部及中段窗墙、凹入侧壁和顶部楼板，裁去新开口中的旧墙、玻璃、楼板及窗边构件。44个对象已并入188版完整校园模型，归档原几何保留。四层楼板从归档原网格恢复8块局部补片，保留材质及插值UV。重开后245个前沿检查点无遮挡、20条纵深视线命中新墙或玻璃、75处正面窗视线命中玻璃；49248个楼板及铺砖覆盖采样点通过，1742点位于补片，未检测到重叠。原187版网格和UV保留。北侧铺砖按完整厚度裁切，补回原凹槽铺砖并封闭东侧斜墙屋面楔形缺口；1995个屋面覆盖点和445个屋顶开口检查点通过。生产CampusViewer私有预览完成6个MAR视角，未修改公开资源。高层整体体量仍近似，完整模型已保存，总览/细节的玻璃几何、UV存在性及材质一致性已通过检查，本轮已发布，但不代表整栋建筑或校园已完成精确还原。代码为web/tools/refine_mar_north188.py，验证为web/tests/verify_mar_north188_blender.py，证据在result/blender/mar-north-candidate/verification.json。

## 建筑核验记录

下表仅记录最近核验范围。具体证据、历史范围与相机参数见web/tools/building-metadata.json。

|楼号|最近核验版|最近范围|
|---|---|---|
|61A|177|Replace the inward-facing uncut slate apron behind ten retained near-corner Kingsway dormers; remove overlapping original roof surfaces locally. Preserve original dormers and unregistered roof areas. Photographic dimensions are estimates; full current roof and interiors remain unverified.|
|CBG|166|Eight entrance leaves now have one thin pane each, with matching apertures through the overlapping curtain panes. User red/orange shades and optical parameters retained.|
|CKK|178|Read-only review of principal elevation, entrance columns, fanlight, window groups and cornices against archived Grimshaw and Willebrand built photographs. Retained164/173 glazing corrections; no reliable additional geometry correction established.|
|CLM|175|按官方物业手册照片补全首层两侧低护栏，曲线位置沿现有Aldwych窗列注册；中央及侧门通路保留。照片日期未知，跨度、高度和杆件尺寸估算；既有玻璃、窗格和上部模型保留。|
|COL|175|下部两条临街立面的普通石柱移除217组错误横缝，保留街角块石，主入口旁3根一层石柱建立浅竖槽。照片拍摄日期未知，浅槽尺度估算；上层窗列和屋顶仍未完整证实。|
|CON|180|Eight previously registered entrance panes now use single outward surfaces with per-corner UV preserved. Lower/front fanlight opacity.82 retained; two supported inner doors use estimated.42 opacity and dielectric metal0. Upper/roof and29unregistered proxies retained.|
|COW|177|Outward normals of all110glass boxes and seated solid roof sheets on11photographed street dormers. No facade-layout, window-count, material-opacity or fullroof-layout change.|
|FAW|176|核对FAW整栋模型、曲折窗带和PAN共用入口归属；未发现照片可证的整片修正，本轮无模型改动。|
|KGS|176|Portugal Street attic now has three central windows and two canted end bays continuing the lower storeys, five main axes and nine outward glazing facets. St Clement’s elevation unchanged.|
|KSW|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|LAK|179|Read-only review retains photo-supported sash windows and dormer apertures; no evidence-supported new geometry correction. Undated official imagery is not a current measured survey.|
|LCH|148|Official May2025 street photograph replaces the historical left lower shopfront glazing with continuous white paneling. Both shop overlights gain the photographed2-row4-column grids, and two fictitious large-pane middle rails are removed. Obscured right basement, original large glass, timber entry and other upper/roof geometry remain unchanged. Dimensions and optical finishes are estimates; no complete interior claimed.|
|5LF|147|11 existing panes retain mesh, UV and original neutral color; finite transmission with explicit browser opacity0.78. Right chimney now carries photograph-supported twin pots across frontage.44 front and44 two-metre behind-glass checks plus two pot first hits passed after reopening. Pot offsets and optical parameters estimated; unseen roof and complete interiors unverified.|
|35L|176|核对2026年5月官方施工通讯的2页及4张局部施工照片；记录入口切割、窗洞扩大与结构施工阶段，保留示意围挡。|
|49L|147|Retained street and corner glazing keeps original mesh, UV and color with explicit browser opacity0.84. Corner round window backing43mm behind glass is locally opened. Latest published2025/26 LSE handbook shows the fire-exit round feature as an opaque horizontal ventilation louvre, replacing its historical glass interpretation. A separate shared upper-wall component trims only proven interference with the widened No50 window; other upper areas retained. Dimensions and optics estimated; capture dates unknown.|
|50L|147|50A entry and opaque external round lamp are located between upper window axes using the2022 planning photograph; frame and lower panel adopt deep blue shown in latest published2025/26 LSE handbook. No50 tripartite upper window widened with true wall clearance, while its inherited4.30–6.32m vertical datum remains estimated because photo top is cropped and reference door height is not surveyed. Other upper windows and original wooden No50 portal retained. Glass browser opacity0.82; no invented complete interior. Shared49L interference is archived and replaced in49L own exterior collection.|
|51L|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|LRB|178|Plaza Café glazing uses66 outward single surfaces in place of66 closed glass boxes, removing duplicate alpha blending. Original outline, per-corner UVs, colour, opacity0.30, frames and café furniture retained. Main library opaque proxy windows and roof unchanged; whole present-day layout not established.|
|MAR|188|按已建照片对齐北立面中段及上部开口，联动窗墙、四层楼板、铺砖和斜向屋面；保留底座三窗及原始网格。开口尺寸与进深估算，高层体量和完整现状内部未核实。|
|OLD|185|入口楼名与校训重新注册并贴合现有石材；楼名适配石柱宽度，保留字体、颜色和全部立面网格。字样尺度及间隙估算，完整外观与内部仍未完成。|
|OCS|145|Restoration photographs support existing three-column wide display plus separately posted narrow display, left solid door, right glazed door and three-column four-row upper sashes. Keep existing subdivisions and finishes. Roof plan and dimensional proportions remain photo estimates, full current interior unverified.|
|PAN|166|Five existing shared entrance glass systems and25 registered frontage windows receive independent clearer dielectric finishes. Existing frames, blinds, geometry and all FAW elevations retained.|
|PAR|180|Photographed street panes receive outward closed-box winding and independent dielectric finish. Coordinates, corner UV, inherited opaque finish and unpictured side/rear panes retained; no unsupported full interior exposed.|
|PEA|146|Two retained podium walls receive real openings matching original entrance and ticket glazing.11 glass elements retain geometry, UV and neutral colour; explicit webOpacity0.82. Original upper3x3 windows, brick side and low wing retained. Unseen roof frame, rear and complete rooms remain unverified.|
|PEL|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|POR|148|Twenty-three retained street and corner glass panels keep their original geometry, UVs and neutral color with explicit browser opacity0.82. Near-window backing checked before enabling transparency; no invented interior added. Undated handbook imagery supports the shopfront. Exact optical properties, roof registration and unseen sides remain estimated.|
|SAR|186|4组首层临街窗使用中性透光玻璃及浅色竖向百叶，保留原玻璃几何、UV、窗框、入口门和上层窗。依据未注明日期的官方照片及2018年街景，百叶布置与光学参数估算，完整内部仍未建立。|
|SAW|166|125 photographed timber-curtain lights use their original outward face and UV, removing duplicated transparent-box backs and edges. Existing stair, timber frames, brick and all room studies retained.|
|SHF|179|Three photographed right dormers use single outward panes; opaque obscured left dormer and all other windows unchanged. Original UVs, tint and opacity retained; dimensions inherited photographic estimates.|
|SAL|184|7条连续闭合山花压顶取代154段重叠杆件；7组玻璃退入原窗洞，补出中央三联窗后的砖墙开口。原压顶路径、窗洞轮廓、光学材质和暖橙褐砖色保留；截面及退入深度估算，完整现状与内部未完成。|
|STC|143|Retains documented38ft by7ft6in panel and frame. A perspective-registered blue Thames curve, six coarse silver landmark silhouettes and limited muted mosaic fields replace the uniform placeholder. Border and text plaque retained. These are native polygon approximations without embedded source images; fine mosaic tesserae, contour accuracy and relief depth remain unmeasured.|

## 保存和发布

188版构建、重开、网页与发布证据记录在result/blender/stage188。Cloudflare部署ID为b17516dd-1754-4b6e-af2d-212cfd3befc7。清理187版旧整模、候选二进制、废弃辅助脚本和重复展示图，共释放192530059字节。历史旧整模仅在当前源文件、线上资源和GitHub核对通过后删除；本轮清理结果见该目录cleanup.json。原始照片、必要组件和证据记录保留。
