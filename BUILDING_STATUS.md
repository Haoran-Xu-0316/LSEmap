# LSEmap模型状态

当前本地完整模型为181版：result/blender/LSE_campus_detailed_v181.blend。已保存并重开验证，6420个对象。

原生SHA256：bfcbe75e064636b372d1a10cf06a41f59985daf6b4745dbf53269a8f611e5517。

本轮统一修正28栋楼的玻璃表面策略：3238个朝内闭合组件改为朝外，3863个闭合组件登记为单侧渲染。原颜色、透明度、顶点及逐角UV保留。单层玻璃仍可从两侧查看。该修正不代表重新核验建筑外形、照片日期或完整内部。

所有建筑完整外观、当前内部结构和每个房间尚未完成。可加载模型、局部修正和核对记录均不代表整栋实测完成。照片拍摄日期未知时不称2026实拍。

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
|MAR|177|107 Great Hall panes and54 mezzanine guards retain their apertures; one sheet per pane replaces six-face boxes.|
|OLD|178|Eight registered Houghton Street ramp posts now use independent black coating while the continuous handrail stays silver. Shapes, matrices and UVs retained; original object archived. Photo capture date unknown and coating values estimated. Whole-building interior layouts remain unfinished.|
|OCS|145|Restoration photographs support existing three-column wide display plus separately posted narrow display, left solid door, right glazed door and three-column four-row upper sashes. Keep existing subdivisions and finishes. Roof plan and dimensional proportions remain photo estimates, full current interior unverified.|
|PAN|166|Five existing shared entrance glass systems and25 registered frontage windows receive independent clearer dielectric finishes. Existing frames, blinds, geometry and all FAW elevations retained.|
|PAR|180|Photographed street panes receive outward closed-box winding and independent dielectric finish. Coordinates, corner UV, inherited opaque finish and unpictured side/rear panes retained; no unsupported full interior exposed.|
|PEA|146|Two retained podium walls receive real openings matching original entrance and ticket glazing.11 glass elements retain geometry, UV and neutral colour; explicit webOpacity0.82. Original upper3x3 windows, brick side and low wing retained. Unseen roof frame, rear and complete rooms remain unverified.|
|PEL|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|POR|148|Twenty-three retained street and corner glass panels keep their original geometry, UVs and neutral color with explicit browser opacity0.82. Near-window backing checked before enabling transparency; no invented interior added. Undated handbook imagery supports the shopfront. Exact optical properties, roof registration and unseen sides remain estimated.|
|SAR|166|Correct explicitly identified legacy exterior glass metallic response to dielectric0. Geometry, UVs, colour, roughness, opacity, transmission, frames and interior studies retained.|
|SAW|166|125 photographed timber-curtain lights use their original outward face and UV, removing duplicated transparent-box backs and edges. Existing stair, timber frames, brick and all room studies retained.|
|SHF|179|Three photographed right dormers use single outward panes; opaque obscured left dormer and all other windows unchanged. Original UVs, tint and opacity retained; dimensions inherited photographic estimates.|
|SAL|176|核对主街立面的砖石分区、18组四联主窗、6组双联山花窗、凸窗、前侧双塔屋顶和历史中央入口；现有窗格保留，本轮无改动。|
|STC|143|Retains documented38ft by7ft6in panel and frame. A perspective-registered blue Thames curve, six coarse silver landmark silhouettes and limited muted mosaic fields replace the uniform placeholder. Border and text plaque retained. These are native polygon approximations without embedded source images; fine mosaic tesserae, contour accuracy and relief depth remain unmeasured.|

## 保存和发布

181版构建、重开、网页与发布证据记录在result/blender/stage181。历史旧整模仅在当前源文件、线上资源和GitHub核对通过后删除；本轮清理结果见该目录cleanup.json。原始照片、必要组件和证据记录保留。
