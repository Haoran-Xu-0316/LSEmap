# LSEmap模型状态

当前本地完整模型为193版：result/blender/LSE_campus_detailed_v193.blend。6497个对象。OLD蓝色涂漆框件反射修正已合入；重开、8项网页检查、125个展示视角刷新及线上资源与页面核对通过。

原生SHA256：795f45f02fae1087a138cb3fd4d63a62869182d5c0cfaab202e4c2a9e98855fb。

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
|LRB|191|Portugal Street侧85块主楼及18块屋顶窗面保留朝外单层表面，移除1030个背面及边面三角形；正面位置、逐角UV、颜色和光学输入保留。18块屋顶窗仍与内部剖视共用，不改变房间结构；其他立面和完整现状内部未核实。|
|MAR|188|按已建照片对齐北立面中段及上部开口，联动窗墙、四层楼板、铺砖和斜向屋面；保留底座三窗及原始网格。开口尺寸与进深估算，高层体量和完整现状内部未核实。|
|OLD|193|20组既有蓝色框件使用12种独立漆面材质，金属度改为0、粗糙度为估计值0.46；原蓝色色值、玻璃、几何和UV保留。Houghton、Clare Market及既有屋顶窗框采用同一漆面策略，完整现状与内部仍未核实。|
|OCS|145|Restoration photographs support existing three-column wide display plus separately posted narrow display, left solid door, right glazed door and three-column four-row upper sashes. Keep existing subdivisions and finishes. Roof plan and dimensional proportions remain photo estimates, full current interior unverified.|
|PAN|166|Five existing shared entrance glass systems and25 registered frontage windows receive independent clearer dielectric finishes. Existing frames, blinds, geometry and all FAW elevations retained.|
|PAR|180|Photographed street panes receive outward closed-box winding and independent dielectric finish. Coordinates, corner UV, inherited opaque finish and unpictured side/rear panes retained; no unsupported full interior exposed.|
|PEA|146|Two retained podium walls receive real openings matching original entrance and ticket glazing.11 glass elements retain geometry, UV and neutral colour; explicit webOpacity0.82. Original upper3x3 windows, brick side and low wing retained. Unseen roof frame, rear and complete rooms remain unverified.|
|PEL|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|POR|148|Twenty-three retained street and corner glass panels keep their original geometry, UVs and neutral color with explicit browser opacity0.82. Near-window backing checked before enabling transparency; no invented interior added. Undated handbook imagery supports the shopfront. Exact optical properties, roof registration and unseen sides remain estimated.|
|SAR|186|4组首层临街窗使用中性透光玻璃及浅色竖向百叶，保留原玻璃几何、UV、窗框、入口门和上层窗。依据未注明日期的官方照片及2018年街景，百叶布置与光学参数估算，完整内部仍未建立。|
|SAW|190|9828块镂空砖与周围墙面齐平，18673处搭接砂浆连接相邻砖层。保留砖块尺寸、UV、颜色及原玻璃和室内；移除砂浆隐藏接触面，安装尺寸仍为照片估计。|
|SHF|179|Three photographed right dormers use single outward panes; opaque obscured left dormer and all other windows unchanged. Original UVs, tint and opacity retained; dimensions inherited photographic estimates.|
|SAL|184|7条连续闭合山花压顶取代154段重叠杆件；7组玻璃退入原窗洞，补出中央三联窗后的砖墙开口。原压顶路径、窗洞轮廓、光学材质和暖橙褐砖色保留；截面及退入深度估算，完整现状与内部未完成。|
|STC|143|Retains documented38ft by7ft6in panel and frame. A perspective-registered blue Thames curve, six coarse silver landmark silhouettes and limited muted mosaic fields replace the uniform placeholder. Border and text plaque retained. These are native polygon approximations without embedded source images; fine mosaic tesserae, contour accuracy and relief depth remain unmeasured.|

## 保存和发布

193版已逐文件提交并push；推送后线上发行清单与本地一致，未重复手动部署。验收时Cloudflare100%部署版本为d9027d7d-b5ad-4104-a7fb-e480f1e7b31e。OLD外观、内部与总览页面无报错、无缺图，入口脚本、目录、展示清单、OLD模型和3段校园模型哈希匹配。总览与近景的二进制几何保持原样，蓝色色值保留，125个展示视角已刷新。清理192版旧整模、旧OLD资源、125张重复展示图、4张与公开展示图相同的私有候选帧及生成缓存，共释放219232410字节。保留193版完整源文件、参考资料与核验记录；清理后最新源文件重开通过。证据见result/blender/stage193。

192版已逐文件提交并push；推送后、未重复手动部署时，线上发行清单已与本地一致。当轮Cloudflare100%版本为c667789c-638b-4ca9-b636-788ba17dd939。已核对入口外观、内部视图及校园总览，脚本、目录、展示清单、OLD资源和3段校园模型哈希匹配，无页面报错或缺图。删除191版旧整模、旧OLD资源、125张重复展示图、6张私有对比原帧及生成缓存，共释放225283242字节。192版完整源文件现已由193版替代，参考资料、对比合图和核验记录保留；当轮清理后重开验证通过。证据见result/blender/stage192。

191版已逐文件提交并push，部署ID为45d11c06-dde9-4dcc-b545-6f27a4cb4e0a。线上LRB外观、内部剖视和校园总览验收通过，脚本、目录、展示清单、LRB资源及3段校园模型的哈希与本地发行包一致。删除190版旧整模、125张重复展示图、旧LRB资源及生成缓存，共释放209645091字节。191版源文件已由192版替代，原始参考资料和核验记录保留；当轮清理后重开验证通过。证据位于result/blender/stage191。

190版当轮完整模型、8项网页检查、逐文件Git提交、线上资源哈希和SAW及总览页面核对通过。证据位于result/blender/stage190，Cloudflare部署ID为ea93b6fe-085c-4378-b265-abb6e0fb0345。已删除189版旧整模、已合入候选组件、重复展示图和生成缓存，共释放192932826字节；190版完整源文件已由191版替代，参考照片保留。

## OLD保护玻璃

189版合入已验证的独立组件，替换原后置面，不叠加玻璃层。原人物、石材、窗框、字样及UV保留；安装间隙和透明度为视觉估计。局部候选的对比记录位于result/blender/old-artwork-glazing，整模重开记录位于result/blender/stage189。雕塑人物细节及完整OLD外观、内部继续完善。

## SAW砖屏与灰缝

2026-10-09：对照EH Smith与ArchDaily照片，将9828块既有砖移回已注册墙面，保留原砖尺寸、颜色、UV及117936个三角面。补出18673处实际搭接灰缝，186730次接触检查通过；移除被砖块遮挡的砂浆顶底面后，新增加149384个三角面，比首轮灰缝方案少74692个。整楼网页导出由12142224字节增至13529872字节，仅增加1个渲染primitive。参考图拍摄日期未知，尺寸与安装关系仍为照片估计。

完整190版已保存并重新打开验证，6494个对象；既有几何、UV、字样、材质绑定和其他集合保留。记录见result/blender/stage190及saw-screen-review。已刷新125张展示图，8项网页检查通过，总览与单楼砂浆边界和材质一致，其他楼和房间资源保持不变。已逐文件提交并push，Cloudflare上线验收通过，旧整模及临时导出已清理。CBG沿用用户指定红色为主、橙色为辅，不作为照片测色结论。

## OLD扶手网页材质

入口照片显示银灰扶手，原生源材质已为金属；网页现有天空反射强度使其偏暗。现将ACCESS钢材与APPROACH银色材质显式绑定共享天空反射，采用柔和高光，不修改蓝色窗框、不新增纹理和网格。已重绘展示图并通过8项检查，入口近景核对完成。该网页修正已逐文件提交并部署，线上脚本及资源哈希匹配，OLD与总览页面无报错、无缺失图片。部署ID为0effc9b2-83b5-46b3-873f-3d8bc489e0be；照片光照与光学参数仍为视觉估计。记录见result/blender/old-access-finish。

## 模型加载优化

本轮在193版模型上加入无损gzip分片及浏览器流式解压，原始49591852字节模型传输降至23073190字节，减少53.47%。支持HTTP自动解压及原始字节解压两种服务器行为；不支持流式解压的浏览器、失败的压缩分片可回退原分片。gzip平台标记已统一，避免Mac和Cloudflare生成不同压缩哈希；分片和完整GLB仍逐项校验，原生源文件、模型资源及125张展示图像素均保持一致。17项加载单元检查、11项桌面和手机网页检查通过；50Mbps、30ms模拟网络下桌面首帧约9.1秒降至4.8秒，该结果不代表实际网络保证。全部网站改动已逐文件提交并push，最终跨平台修正推送后线上发行清单自动与本地一致。验收时Cloudflare100%版本为1d962ab2-e579-4446-b5e4-18a752b19fba；已核对应用资源、3段压缩模型及目录哈希，桌面、手机、OLD外观与内部视图通过，无缺图或报错、无原始分片回退。删除221项过期生成图库、重复渲染、无引用构建副本及缓存，共释放73690025字节；193版完整源模型、参考资料及核验记录保留，所有运行资源和源模型清理后哈希检查通过。证据见result/web/loading-optimization。

校园GLB约49.6MB，现由三个既有分片并行下载、逐段校验后合并；提前准备Draco解码器，解码worker按设备配置限制为2至4。模型源、几何与纹理不变。优化前线上首载一次实测11441ms，网络环境影响较大，第一轮线上复测11668ms，未证实总耗时改善；再将目录、展示清单和3D程序并行准备，最终线上复测10467ms，较原11441ms减少974ms，单次结果受网络影响，不能作为保证。已全部push并部署a65e7a3e-2e67-40ca-a9f2-f3fa0c730f42，线上资源和OLD、总览页面核对通过。10项加载单元检查、11项网页和传输检查通过。清理25个已逐项确认合入190版的旧组件及125张重复展示图、生成缓存，释放78671517字节。证据见result/cleanup/loading-final与result/web。

## LRB临街玻璃表面

191版将已注册Portugal Street窗面从闭合盒体改为单层光学表面，85块主楼窗及18块屋顶窗移除1030个多余三角形。逐窗核对正面坐标、朝向、逐角UV和完整光学输入；原几何保留在完整源文件内。朝街窗位沿用2025年4月现有立面图注册，比例与窗部尺寸仍为估算；未经核实的房间保留原不透明代理状态，其他立面、屋顶体量和内部结构不因本轮视为完成。证据见result/blender/stage191。

## OLD入口玻璃光学修正

192版降低八块现有门玻璃的灰绿色罩色与网页透明度，保留原玻璃几何、逐角UV、粗糙度和透射参数。72条入口采样射线未发现4m内旧代理遮挡，未据包围盒重叠盲目删除窗面或墙体。生产CampusViewer私有对比完成入口近景、整楼及门部近景；已有台阶、红色墙面和入口层次更清楚。参考为用户提供的照片，拍摄日期未知；光学值为视觉估计，既有门厅基于历史资料，不代表完整当前内部。证据见result/blender/old-exterior-colour-review及stage192。

## OLD蓝色涂漆框件

193版把20组已识别的蓝色涂漆框件改为介电漆面，12种独立材质保留原蓝色色值，仅改变金属度与粗糙度。主入口、Clare Market和阁楼窗框沿用既有几何与UV，不改变玻璃透明度、银色扶手或已独立修正的壁灯。资料为用户提供的Clare Market照片及Webb Yates已建项目照片06，拍摄日期未知；粗糙度0.46是视觉估计。完整当前外观、内部结构及全部房间仍未完成。证据见result/blender/old-painted-frame-review与stage193。

## 2026-10-14补充核对与清理

重新核对线上发行清单、入口脚本、目录和3段压缩模型，均与本地193版一致。17项加载检查通过；1440px桌面和390px手机实测均使用压缩分片，无原始分片回退、页面报错、缺图或横向溢出。删除3个未跟踪且当前目录、图库和发行清单均未引用的LRB/OLD旧导出，并清理可再生缓存，共释放36628722字节。193版完整源文件及全部保留运行模型、展示图哈希通过核对。证据见result/web/loading-optimization/current-live-check.json、current-browser-check.json及result/cleanup/loading-optimization-final/cleanup.json。

## CBG屋顶待核对候选

独立候选修正顶部端面开口、分层屋面和低玻璃护栏，并保留原始归档网格。裁切保留204278个未受影响低层面的精确原生顶点、材质及逐角UV；12条局部视线、36组裁切实体闭合检查和6个生产渲染器对比视角通过。屋面范围、设备围护和上层楼梯位置仍未完整注册，悬挂灰色构件功能未确认，2016年剖面仅作设计资料。候选保存在result/blender/cbg-roof-candidate，工具为web/tools/refine_cbg_roof_envelope.py，检查为web/tests/verify_cbg_roof_candidate_blender.py；未合入193版或发布到网站，不代表整栋或校园完成。
