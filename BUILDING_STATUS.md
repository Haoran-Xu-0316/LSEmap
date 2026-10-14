# LSEmap模型状态

当前完整原生模型：result/blender/LSE_campus_detailed_v198.blend。

原生SHA256：b45a6a433f350226beecfd201457420d86b2d253796098f86ff5417d5752b27e。

31栋楼有目录记录，30栋有独立外观，25个内部视图、15个独立房间研究。可加载不等于整栋实测完成；完整内部、每间房和未见立面仍未完成。未注明日期的照片不称最新实测。

## 本轮范围

198版将397块既有沥青路段合并成一张连续闭合路网，原138个路段对象归档，消除约6563平方米重复共面覆盖。原道路外缘、23个孔洞和地面高度保留；计算清理的边界偏差低于0.1毫米。此项解决接头重复面，未推断新道路、车道宽度或路缘实测。

6828个原对象的几何、UV、材质绑定逐项保持，新完整模型保存后重开检查。所有建筑外观、默认内部和15个独立房间资产与197版保持相同字节。

天空改为Poly Haven的CC0晴间多云素材，比旧图减少342463字节。俯视建筑恢复明亮中性背景，接近水平的街景显示天空；视角阈值加入滞回，背景和玻璃共享一份静态环境纹理，旋转时不重新捕获。

CON和PAN分别核对现有模型与官方照片。资料仍未覆盖上层及屋顶，没有据此猜测修改；这些区域和完整当前内部仍未完成。

总览、选楼和127张图库使用同一生产渲染器，发行前校验素材、模型与图库哈希。

## 建筑核验范围

具体资料、相机与历史限制见web/tools/building-metadata.json。下表只记录最近明确核验范围。

|楼号|最近核验版|最近范围|
|---|---|---|
|61A|177|Replace the inward-facing uncut slate apron behind ten retained near-corner Kingsway dormers; remove overlapping original roof surfaces locally. Preserve original dormers and unregistered roof areas. Photographic dimensions are estimates; full current roof and interiors remain unverified.|
|CBG|194|涂漆遮阳构件采用介电涂层，中性玻璃透明度调整。红色为主遵循用户选择；屋顶候选尚未合入。|
|CKK|178|Read-only review of principal elevation, entrance columns, fanlight, window groups and cornices against archived Grimshaw and Willebrand built photographs. Retained164/173 glazing corrections; no reliable additional geometry correction established.|
|CLM|196|统一临街灰暖白石材、深棕涂饰窗框与木门；玻璃粗糙度调整，原色值、透明度、透射、几何和旧UV保留。上层照片受树遮挡，不声称新测绘。|
|COL|195|临街石材、涂漆窗框、木门和玻璃材质分离；32个原对象仅替换材质，原几何、旧UV及透明度保留。|
|CON|180|Eight previously registered entrance panes now use single outward surfaces with per-corner UV preserved. Lower/front fanlight opacity.82 retained; two supported inner doors use estimated.42 opacity and dielectric metal0. Upper/roof and29unregistered proxies retained.|
|COW|177|Outward normals of all110glass boxes and seated solid roof sheets on11photographed street dormers. No facade-layout, window-count, material-opacity or fullroof-layout change.|
|FAW|197只读复核|核对FAW整栋模型、曲折窗带和PAN共用入口归属；未发现照片可证的整片修正，本轮无模型改动。|
|KGS|176|Portugal Street attic now has three central windows and two canted end bays continuing the lower storeys, five main axes and nine outward glazing facets. St Clement’s elevation unchanged.|
|KSW|195|整段砖、石、窗框、店面、木门及玻璃颜色修正，补12根上层侧窗中梃；屋顶及后立面仍缺完整证据。|
|LAK|179|Read-only review retains photo-supported sash windows and dormer apertures; no evidence-supported new geometry correction. Undated official imagery is not a current measured survey.|
|LCH|148|Official May2025 street photograph replaces the historical left lower shopfront glazing with continuous white paneling. Both shop overlights gain the photographed2-row4-column grids, and two fictitious large-pane middle rails are removed. Obscured right basement, original large glass, timber entry and other upper/roof geometry remain unchanged. Dimensions and optical finishes are estimates; no complete interior claimed.|
|5LF|147|11 existing panes retain mesh, UV and original neutral color; finite transmission with explicit browser opacity0.78. Right chimney now carries photograph-supported twin pots across frontage.44 front and44 two-metre behind-glass checks plus two pot first hits passed after reopening. Pot offsets and optical parameters estimated; unseen roof and complete interiors unverified.|
|35L|176|核对2026年5月官方施工通讯的2页及4张局部施工照片；记录入口切割、窗洞扩大与结构施工阶段，保留示意围挡。|
|49L|147|Retained street and corner glazing keeps original mesh, UV and color with explicit browser opacity0.84. Corner round window backing43mm behind glass is locally opened. Latest published2025/26 LSE handbook shows the fire-exit round feature as an opaque horizontal ventilation louvre, replacing its historical glass interpretation. A separate shared upper-wall component trims only proven interference with the widened No50 window; other upper areas retained. Dimensions and optics estimated; capture dates unknown.|
|50L|147|50A entry and opaque external round lamp are located between upper window axes using the2022 planning photograph; frame and lower panel adopt deep blue shown in latest published2025/26 LSE handbook. No50 tripartite upper window widened with true wall clearance, while its inherited4.30–6.32m vertical datum remains estimated because photo top is cropped and reference door height is not surveyed. Other upper windows and original wooden No50 portal retained. Glass browser opacity0.82; no invented complete interior. Shared49L interference is archived and replaced in49L own exterior collection.|
|51L|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|LRB|196|统一低对比棕砖和暖灰缝，屋顶高起围护改为照片支持的深灰，涂饰窗框降低金属感并减轻乳蓝反射。原几何、UV、透明穹顶、café玻璃及内部保留。|
|MAR|188/195复核|保留188北立面开口及楼板修正；195三向整体核对未形成可证的新形体修正，未重复加屋面。|
|OLD|194/196门厅|外墙沿用194版石材修正；196完善历史门厅的石材接缝、深色入口地垫与浅色圆盘灯。保留台阶、门槛和房间注册，不代表完整当前内部。|
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
|STC|197外观/143艺术板|Retains documented38ft by7ft6in panel and frame. A perspective-registered blue Thames curve, six coarse silver landmark silhouettes and limited muted mosaic fields replace the uniform placeholder. Border and text plaque retained. These are native polygon approximations without embedded source images; fine mosaic tesserae, contour accuracy and relief depth remain unmeasured.|
