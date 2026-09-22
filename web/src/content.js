/** Public display copy: source-aware descriptions, not claims of measured accuracy. */
export const statusNames = {
  detailed: "已深化建筑模型",
  massing: "简化体量模型",
  provisional: "轮廓归属待确认",
  construction: "施工地块",
  unlocated: "独立轮廓待确认",
};
export const buildingDetails = {
  MAR: {
    description:
      "混凝土立面下是通透的Grand Hall。查看大厅围护、树状柱、弧形楼梯与夹层栏杆的连接。",
    note: "大厅开洞、楼梯半径与家具布局依据照片比例估计，未复刻全部楼层。",
    images: [
      ["mar-exterior", "Marshall Building立面"],
      ["mar-hall", "Grand Hall公共大厅"],
      ["mar-stair", "弧形楼梯与平台连接"],
    ],
  },
  SAW: {
    description:
      "折面红砖表皮围合Sheffield Street转角。立面凹折、透空砖屏与窗洞形成丰富层次。",
    note: "砖屏为几何重建；内部仅为螺旋楼梯研究，不代表完整功能布局。",
    images: [
      ["saw-exterior", "Saw Swee Hock折面立面"],
      ["saw-brick", "透空砖屏细节"],
    ],
  },
  CBG: {
    description:
      "Centre Building以竖向遮阳构件组织立面，面向Houghton Street形成开放的首层空间。",
    note: "已深化遮阳构件与局部公共内部，尺寸和室内位置仍含估计。",
    images: [["cbg-exterior", "Centre Building遮阳构件"]],
  },
  LRB: {
    description:
      "图书馆的螺旋坡道、垂直交通与顶部采光共同构成中庭。切换公共内部可单独观察空间关系。",
    note: "坡道半径、标高和书架布置为研究性估计，未恢复全部藏书布局。",
    images: [["lrb-interior", "图书馆螺旋坡道与电梯"]],
  },
  CKK: {
    description:
      "历史建筑外壳中嵌入明亮的公共中庭，木饰面、楼梯和天窗构成空间的主要层次。",
    note: "中庭家具、细部尺度和部分顶部结构根据公开图片估计。",
    images: [["ckk-interior", "Cheng Kin Ku公共中庭"]],
  },
  OLD: {
    description:
      "Houghton Street的传统石材立面，以入口、门廊与连续窗列呈现校园历史建筑的尺度。",
    note: "入口及窗套已深化，雕饰简化，未建立完整内部。",
    images: [["old-exterior", "Old Building入口"]],
  },
  SAL: {
    description:
      "面向Lincoln’s Inn Fields的Sir Arthur Lewis Building，以砖石立面、连续窗列和底部入口呈现历史街区尺度。",
    note: "立面主要尺度依据照片估计，未见背面仍简化。",
    images: [["sal-exterior", "Sir Arthur Lewis Building沿街立面"]],
  },
  CLM: {
    description:
      "面向Aldwych的凸弧石材立面，配以柱列门廊、檐口和带老虎窗的阁楼屋顶。",
    note: "门廊雕饰为简化形态，后侧与屋顶设备未逐项复刻。",
    images: [["clm-exterior", "Clement House的Aldwych立面"]],
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
  if (buildingDetails[building.code]) return buildingDetails[building.code];
  const descriptions = {
    unlocated:
      "已建立楼宇资料条目，尚未确认独立建筑轮廓，地图中不虚构位置或形体。",
    provisional:
      "当前展示暂定归属的建筑体量，轮廓与代码对应关系仍需进一步确认。",
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
