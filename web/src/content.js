/** Public display copy: source-aware descriptions, not claims of measured accuracy. */
export const statusNames = {
  detailed: "已深化建筑模型",
  facade: "沿街立面研究",
  massing: "简化体量模型",
  provisional: "轮廓边界待校准",
  construction: "施工地块",
  unlocated: "独立轮廓待确认",
};
export const buildingDetails = {
  "35L": {
    description: "2026年7月的施工记录显示，35L主体结构、立面修复、Agora钢构和CLT结构施工正在推进。",
    note: "当前仅展示示意围挡。已核验照片覆盖局部施工空间，无法可靠定位完整施工体量；不将未来竣工方案作为现状。依据LSE2026年7月建设通讯，非当前实时进度。",
    images: [],
  },
  "49L": {
    description: "Coopers餐厅占据Lincoln’s Inn Fields与Portsmouth Street的转角。蓝色底层、白色推拉窗、百叶窗板和带雨篷的斜角入口构成街面特征。",
    note: "位置与外轮廓依据2022年规划总图配准至校园模型，外观参考归档照片。楼高、窗距、屋顶和未见背面仍为估计；图示外壳不等同餐厅全部产权或租赁范围。",
    images: [["49l-exterior", "Coopers转角门面与蓝色底层"]],
  },
  "61A": {
    description: "61 Aldwych保留石材街角立面，中部三层窗带采用连续石柱与深色金属窗间板，屋顶角亭改为切角轮廓、下层分格窗、环绕玻璃窗带和八面斜屋顶。",
    note: "沿街外观依据改造前归档照片深化。61A已确认为LSE物业，模型占地边界及与邻楼衔接仍待校准，楼高、窗距、屋顶进深和未见背面仍为估计；未将未来改造方案或内部效果图作为现状建模。",
    images: [["61a-belts", "三层连续石柱与金属窗间板"], ["61a-pavilion", "切角屋顶角亭与环绕窗带"], ["61a-exterior", "61 Aldwych转角入口与石材立面"]],
  },
  "5LF": {
    description: "Lincoln’s Inn Fields北侧的四层排屋，以黄褐色砖墙、三列白色推拉窗和浅色底层构成立面。入口台阶、黑色栏杆与两侧烟囱已加入模型。",
    note: "用LSE官方地址地图定位点匹配OSM独立轮廓，正面参考归档照片。楼高、窗距、屋顶与未见背面仍为估计；未建立内部。",
    images: [["5lf-exterior", "5 Lincoln’s Inn Fields砖立面与入口"]],
  },
  "COW": {
    description: "Cowdray House以红砖、浅色转角石带和斜折屋顶形成街道轮廓。细窗格、尖顶屋顶窗、齿饰檐口与转角石材门廊呈现近看的层次。",
    note: "沿街立面依据归档照片继续细化，保留原有地图轮廓。楼高、窗距、装饰截面、屋顶进深与未见背面仍为估计；未建立内部。",
    images: [["cow-exterior", "Cowdray House屋顶窗与砖石转角"], ["cow-entrance", "Cowdray House拱券、柱饰与入口细节"]],
  },
  "KGS": {
    description: "King’s Chambers的两组石材凸窗向街道展开，铅色弧顶与三角山花构成屋顶轮廓。中央入口保留拱券、卷饰和带金色字样的绿色铭牌。",
    note: "沿街外观与入口根据归档照片继续细化，保留原有地图轮廓。楼高、窗距、装饰截面、屋顶进深与未见背面仍为估计；未建立内部。",
    images: [["kgs-exterior", "King’s Chambers凸窗与弧顶"], ["kgs-entrance", "King’s Chambers石材拱券与绿色入口铭牌"]],
  },
  LAK: {
    description: "Lakatos Building的两侧街面分别采用大幅店面玻璃和拱形底层窗，上层保留细格推拉窗、石材窗楣、转角石带与齿饰檐口。",
    note: "根据归档照片深化两侧立面。窗数、屋顶坡度、屋顶窗位置与未见背面仍为估计；历史山花的位置尚未确认，未纳入模型。",
    images: [["lak-exterior", "Lakatos转角砖石立面与坡顶"], ["lak-windows", "广场侧拱窗、细窗格与石材窗饰"]],
  },
  LCH: {
    description: "Lincoln Chambers中央拱窗与上层三联窗连接两侧石材凸窗，红棕砖墙与浅色窗框相间。首层宽店窗围合退入式三拱门廊，保留绿色铭牌、木门与棋盘地面。",
    note: "沿街立面依据LSE2025年照片及建筑名录重建；立面配准、尺度和装饰尺寸仍为估计。背面与屋顶简化，屋顶窗位置未确认，未建立内部。",
    images: [["lch-exterior", "Lincoln Chambers沿街立面"], ["lch-entrance", "凹入门廊、三面拱口与棋盘地面"]],
  },
  "50L": {
    "description": "Portsmouth Street的50/50A连续门面以红砖、浅色窗框和石材拱形入口展开。50号入口与相邻餐厅分别定位，保留各自的街面尺度。",
    "note": "根据2022年规划总图修正楼体位置，外壳覆盖50/50A连续建筑，不代表50L独占全部铺面。楼高、窗距、屋顶与未见背面仍为估计；未建立内部。",
    "images": [
        [
            "50l-exterior",
            "50 Lincoln’s Inn Fields沿街立面"
        ]
    ]
},
  "51L": {
    "description": "51 Lincoln’s Inn Fields的红砖窗列与浅色底层、转角石带相接，体现街角建筑的竖向比例。",
    "note": "沿街立面首轮研究，依据归档照片与地图轮廓搭建。楼高、窗距、屋顶进深与未见背面仍为估计；未建立内部。",
    "images": [
        [
            "51l-exterior",
            "51 Lincoln’s Inn Fields街角"
        ]
    ]
},
  "PAR": {
    description: "Parish Hall的低入口门厅与四组窗列形成高低错落的街面。尖拱砖券、题字横梁和十字饰件标识入口，高窗采用粗中央分隔，红瓦坡屋顶设四座深色屋顶窗、两个通风帽和圆形烟囱筒。",
    note: "窗列和屋顶构件参考学校2015年改造资料及2025/26版物业手册。照片拍摄日期、尺寸及当前屋顶设备位置未核实；尚未完成整栋内部。",
    images: [["par-exterior", "Parish Hall低门厅与红瓦坡屋顶"], ["par-entrance", "Parish Hall尖拱砖券与题字入口"], ["par-roof", "Parish Hall尖拱窗列与屋顶通风帽"]],
  },
  "PEA": {
    "description": "Peacock Theatre入口为蓝黑色门面、黄铜星形装饰和暖色雨棚灯。上部为三列窗的浅色体量，右侧较低并设屋顶百叶，侧面保留深色砖墙。",
    "note": "依据场馆现行页面实拍建模，图片上传路径为2023年，准确拍摄日期未核实。楼高、体量分界与未见立面为估算，内部保留既有模型。",
    "images": [["pea-exterior", "Peacock Theatre外观"], ["pea-frontage", "入口、星形装饰与高低体量"], ["pea-side", "砖墙侧面与低位百叶"], ["pea-interior", "剧院内部"]]
},
  "PEL": {
    "description": "Pethick-Lawrence House入口采用外挑银色金属门楣、黄色侧边、首层窗盒和旋转玻璃门。",
    "note": "入口依据未注明拍摄日期的校方照片及2021年公共空间资料建模，尺寸与色彩为估算。塔楼上层窗列、屋顶和完整内部仍待核准。",
    "images": [["pel-exterior", "Pethick-Lawrence House塔楼"], ["pel-entrance", "银色门楣与旋转玻璃门"]]
},
  "POR": {
    "description": "1 Portsmouth Street的The Gilded Acorn转角书店：斜切入口、外挑招牌、铅条橱窗、街名牌与上层木窗分别建模，配以暖色砖墙、灰白窗框和照片可见的屋顶烟囱。",
    "note": "店名依据LSE现行商店页面更新；实拍日期未知，楼高、窗距及隐藏屋顶仍为估计，未建立内部。",
    "images": [
        [
            "por-exterior",
            "1 Portsmouth Street转角与店面"
        ],
        ["por-entrance", "转角入口、铅条橱窗与街名牌"],
        ["por-roof", "转角红砖、烟囱与屋顶栏杆"]
    ]
},
  "SAR": {
    "description": "Sardinia House的红砖立面配以浅色窗台、分格窗和入口名称牌，首层上方补充连续檐口与齿饰。",
    "note": "沿街立面首轮研究，依据归档照片与地图轮廓搭建。楼高、窗距、屋顶进深与未见背面仍为估计；未建立内部。",
    "images": [
        [
            "sar-exterior",
            "Sardinia House红砖立面"
        ]
    ]
},
  "SHF": {
    "description": "Sheffield Street长立面以四组白色多格窗、两层浅色基座与棕色砖墙组成，屋顶设四个宽窗与灰色斜坡屋面。",
    "note": "依据官方照片修正四组窗和斜坡屋顶；层高、屋面进深及背面仍为估计，内部待补。",
    "images": [
        [
            "shf-exterior",
            "Sheffield Street四开间立面"
        ],
        ["shf-roof", "四个屋顶窗与棕砖窗列"]
    ]
},
  STC: {
    description: "St Clement’s的Clare Market长立面以凹入窗列展开，退后的顶层与转角红色平台形成高低层次。入口保留红色门侧、灰色招牌、玻璃门与花槽。",
    note: "依据归档照片深化外观。壁画仅保留面板位置；楼高、窗距、入口具体开间与未见背面仍为估计，未建立内部。",
    images: [
      ["stc-exterior", "St Clement’s窗列与转角平台"],
      ["stc-entrance", "红色门侧、招牌与凹入入口"],
    ],
  },
  COL: {
    description:
      "Columbia House以浅色石材立面沿Aldwych与Houghton Street转角展开。凹入窗洞、石材分缝、连续檐口与Garrick转角店面构成沿街层次。",
    note: "已深化街面及木门入口；窗列节奏、屋顶和未见背面为估计，未建立完整内部。",
    images: [
      ["col-exterior", "Columbia House沿街石材立面"],
      ["col-entrance", "木门、铭牌与石门廊"],
    ],
  },
  CON: {
    description:
      "Connaught House的Aldwych入口以下部灰色花岗岩、上部浅色石材和层叠石檐形成层次，后退的玻璃门保留门廊进深。",
    note: "入口依据实拍重建，上层窗列仍有估计。内部新增CON.7.04会议室样本，依据历史照片和平面图研究，不代表当前布局或整栋内部。",
    images: [
      ["con-entrance", "Connaught House凹入门廊"],
      ["con-exterior", "Aldwych立面与入口位置"],
      ["con-interior", "CON.7.04会议室，八席长桌与木饰面"],
    ],
  },
  MAR: {
    description: "Marshall Building北立面的遮阳构件形成有进深的折面，中央入口由斜向混凝土、后退玻璃和露台栏杆围合。上部遮阳片前缘收窄，北侧退台补充浅色铺装、金属栏杆与局部种植。可近看入口，再进入Grand Hall查看树状柱与弧形楼梯。",
    note: "立面构件、退台高度、铺装与种植位置依据实拍比例估计；色彩为中性光照下的视觉近似，内部仅涵盖公共大厅和局部教室。",
    images: [
      ["mar-exterior", "Marshall Building北立面"],
      ["mar-academic-wings", "办公翼窗格"],
      ["mar-lse-sign", "LSE立体标志"],
      ["mar-entrance", "斜向入口、露台玻璃与前场灯柱"],
      ["mar-hall", "Grand Hall公共大厅"],
      ["mar-stair", "弧形楼梯与平台连接"],
      ["portsmouth-street", "Portsmouth Street铺装"],
      ["portsmouth-bench", "街道长椅与铺装"],
      ["portsmouth-drainage", "石材接缝与排水篦子"],
    ],
  },
  SAW: {
    description:
      "折面红砖表皮围合Sheffield Street转角。立面凹折、透空砖屏与窗洞形成丰富层次。",
    note: "砖屏为几何重建；内部补充螺旋楼梯内外扶手和托架，仍不代表完整功能布局或实际通行条件。",
    images: [
      ["saw-exterior", "Saw Swee Hock折面立面"],
      ["saw-brick", "透空砖屏细节"],
      ["saw-globe", "The World Turned Upside Down"],
      ["sheffield-street", "Sheffield Street"],
    ],
  },
  CBG: {
    description:
      "Centre Building以红色为主、橙色侧面的遮阳构件组织立面，配合灰白框架与玻璃幕墙。面向Houghton Street形成开放的首层空间。",
    note: "已深化遮阳构件与局部公共内部，尺寸和室内位置仍含估计。",
    images: [["cbg-exterior", "Centre Building遮阳构件"]],
  },
  LRB: {
    description:
      "广场侧立面以宽幅分格窗、砖墙和浅色石带组成。顶部朝北斜切的圆顶为螺旋坡道及玻璃电梯中庭采光。",
    note: "广场侧参考2008年照片，窗距与层高为估计；2025年计划更换的闸机及新增屋顶设备布局未核实。",
    images: [["lrb-exterior", "图书馆广场侧窗格与石带"], ["lrb-roof", "斜屋面与北向采光顶"], ["lrb-interior", "图书馆螺旋坡道与电梯"], ["watkins-plaza", "John Watkins Plaza长椅与铺装"]],
  },
  CKK: {
    description:
      "面向Lincoln’s Inn Fields的石材立面以中央拱形门厅、两侧窄窗组和双排老虎窗坡顶组成。屋顶设玻璃会议亭和遮阳露台，内部设木饰面公共中庭。",
    note: "屋顶及中庭尺寸依据照片估计。2025/26计划中的Cafe54改造后布局尚未核实。",
    images: [["ckk-exterior", "Cheng Kin Ku正立面与坡屋顶"], ["ckk-entrance", "中央拱形采光窗与柱式门厅"], ["ckk-roof-pavilion", "玻璃会议亭与遮阳露台"], ["ckk-interior", "Cheng Kin Ku公共中庭"]],
  },
  OLD: {
    description:
      "Houghton Street的传统石材立面，以入口、门廊与连续窗列呈现校园历史建筑的尺度。",
    note: "立面雕刻和尺寸依据照片估计。OLD.4.10展示历史阶梯教室布局。",
    images: [["old-exterior", "Old Building外观"], ["old-houghton-entrance", "Houghton Street拱门与蓝色窗框"], ["old-relief", "入口人物浮雕"], ["old-heraldry", "入口石雕校徽"], ["old-entablature", "Houghton Street檐口与阁楼窗"], ["old-clare-market", "Clare Market蓝窗与入口"], ["old-interior", "OLD.4.10阶梯教室，三组座席与教学墙"]],
  },
  SAL: {
    description:
      "面向Lincoln’s Inn Fields的Sir Arthur Lewis Building，以砖石立面、连续窗列和底部入口呈现历史街区尺度。",
    note: "立面主要尺度依据照片估计，未见背面仍简化。",
    images: [["sal-exterior", "Sir Arthur Lewis Building沿街立面"], ["sal-oriels", "凸窗侧窗与蓝色窗框"]],
  },
  CLM: {
    description:
      "面向Aldwych的凸弧石材立面，配以柱列门廊、檐口和带老虎窗的阁楼屋顶。",
    note: "门廊雕饰、后侧与屋顶仍有简化。内部新增CLM.1.01小组教室，三角桌、木墙裙和窗户依据历史资料研究，尺寸估算。",
    images: [["clm-exterior", "Clement House的Aldwych立面"], ["clm-capitals", "入口柱头卷饰"], ["clm-interior", "CLM.1.01小组教室，四组三角桌与木墙裙"]],
  },
  KSW: {
    description:
      "Kingsway短边入口以石门廊嵌入红砖墙面，中央凸窗、石窗套与蓝色门灯形成辨识特征。",
    note: "主门面方向已根据资料校正；背面和屋顶仍为简化形态。",
    images: [["ksw-exterior", "20 Kingsway完整主立面"]],
  },
  OCS: {
    description:
      "低矮的Old Curiosity Shop藏在现代建筑之间。不对称瓦屋顶、深绿木店面与墙面题字保留其鲜明尺度。",
    note: "依据2023年发布的修复完成照片，不代表当前经营或实景状态。",
    images: [
      ["ocs-exterior", "Old Curiosity Shop街景"],
      ["ocs-roof", "瓦屋顶与木框门窗"],
    ],
  },
  PAN: {
    description:
      "与Fawcett House相接的灰色预制板塔楼。水平窗带延伸至转角，底部为双旋转门共用入口。",
    note: "13层依据地图属性，44m高度为估计；入口家具位置参考照片。",
    images: [
      ["pan-faw-exterior", "Pankhurst与Fawcett整体立面"],
      ["pan-faw-entrance", "双旋转门与镂空门楣"],
    ],
  },
  FAW: {
    description:
      "与Pankhurst House形成连续塔楼界面，灰色板缝、细金属窗框与部分遮帘表现立面节奏。",
    note: "共墙依据地理轮廓处理，未添加假窗；楼层高度仍为估计。",
    images: [
      ["pan-faw-exterior", "Pankhurst与Fawcett整体立面"],
      ["pan-faw-entrance", "共用入口细节"],
    ],
  },
};

export function detailFor(building) {
  const existing = buildingDetails[building.code];
  if (existing) {
    let exteriorImages = building.closeupImage && !existing.images.some(([name]) => name === building.closeupImage)
      ? [...existing.images, [building.closeupImage, `${building.name}${building.detailView.label}`]] : existing.images;
    exteriorImages = [...exteriorImages, ...(building.interiorSpaces || []).map(space => [space.gallery, space.label])];
    if (!building.interiorStudy) return { ...existing, images: exteriorImages };
    const imageName = `${building.code.toLowerCase()}-interior`;
    const images = exteriorImages.some(([name]) => name === imageName)
      ? exteriorImages : [...exteriorImages, [imageName, building.interiorStudy.label]];
    const note = existing.note.replace(/未建立内部|未建内部/g, "未建立完整内部");
    return { ...existing, images, note: `${note}${building.interiorStudy.scope}` };
  }
  const descriptions = {
    unlocated:
      "已建立楼宇资料条目，尚未确认独立建筑轮廓，地图中不虚构位置或形体。",
    provisional:
      "建筑身份已确认，模型占地边界及与相邻建筑的衔接仍待校准。",
    construction: "当前保留施工地块，不将未来方案效果图作为已经建成的建筑。",
    massing:
      "已按地图轮廓建立简化建筑体量。立面节奏和高度为估计，细节将继续完善。",
  };
  return {
    description: descriptions[building.status],
    note: "本页用于建筑形态展示，不作为实际位置、通行条件或室内布局的精确依据。",
    images: [],
  };
}
