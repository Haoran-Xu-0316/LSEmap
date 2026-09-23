import "./style.css";
import { startReleaseSync } from "./release-sync.js";
import { detailFor, statusNames } from "./content.js";

const $ = (selector) => document.querySelector(selector);
const sidebar = $("#sidebar");
const stage = $("#stage");
const list = $("#building-list");
const detailPanel = $("#detail-panel");
const mobile = matchMedia("(max-width: 700px)");
let buildings = [];
let modelRevision = "";
let viewer;
let current = null;
let detailedOnly = false;
let gallery = [];
let galleryIndex = 0;
let loadAttempt = 0;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function setSidebar(open) {
  sidebar.classList.toggle("closed", !open);
  $("#index-toggle").setAttribute("aria-expanded", String(open));
  if (!open) sidebar.classList.remove("show-detail");
  stage.classList.toggle("detail-open", open && Boolean(current));
}

function renderList() {
  const query = $("#building-search").value.trim().toLocaleLowerCase();
  const filtered = buildings.filter(
    (building) =>
      (!detailedOnly || building.status === "detailed") &&
      `${building.code} ${building.name} ${building.address}`
        .toLocaleLowerCase()
        .includes(query),
  );
  list.replaceChildren();
  for (const building of filtered) {
    const row = element("button", "building-row");
    row.dataset.code = building.code;
    row.setAttribute(
      "aria-label",
      `${building.code} ${building.name}，${statusNames[building.status]}`,
    );
    row.append(
      element("span", "building-code", building.code),
      element("span", "building-name", building.name),
    );
    const marker = element(
      "span",
      building.status === "detailed" ? "status-dot" : "row-arrow",
      building.status === "detailed" ? "" : "›",
    );
    marker.setAttribute("aria-hidden", "true");
    row.append(marker);
    row.addEventListener("click", () => selectBuilding(building.code));
    list.append(row);
  }
  $("#result-count").textContent = `${filtered.length}个楼宇条目`;
  $("#empty-search").hidden = Boolean(filtered.length);
}

function showGallery(images, index) {
  gallery = images;
  galleryIndex = index;
  renderGallery();
  $("#gallery-dialog").showModal();
}

function galleryImageUrl(name) {
  return `/images/${name}.webp?v=16-${modelRevision.slice(0, 12)}`;
}

function renderGallery() {
  const [name, caption] = gallery[galleryIndex];
  $("#gallery-image").src = galleryImageUrl(name);
  $("#gallery-image").alt = caption;
  $("#gallery-title").textContent = caption;
  $("#gallery-position").textContent =
    `${galleryIndex + 1} / ${gallery.length}`;
  $("#gallery-prev").disabled = gallery.length === 1;
  $("#gallery-next").disabled = gallery.length === 1;
}

function renderDetail(building) {
  const details = detailFor(building);
  detailPanel.replaceChildren();
  const back = element("button", "back-button", "← 返回建筑目录");
  back.addEventListener("click", () => overview(true));
  detailPanel.append(
    back,
    element("p", "detail-code", building.code),
    element("h2", "", building.name),
    element("p", "detail-address", building.address),
  );
  if (details.images.length) {
    const photo = element("button", "detail-photo");
    photo.setAttribute("aria-label", `放大查看${details.images[0][1]}`);
    const image = element("img");
    image.src = galleryImageUrl(details.images[0][0]);
    image.alt = details.images[0][1];
    image.width = 500;
    image.height = 360;
    photo.append(image, element("span", "", "查看细节 ↗"));
    photo.addEventListener("click", () => showGallery(details.images, 0));
    detailPanel.append(photo);
  }
  detailPanel.append(element("p", "model-state", statusNames[building.status]));
  const actions = element("div", "detail-actions");
  if (building.bounds) {
    const exterior = element("button", "", "建筑外观");
    exterior.id = "exterior-view";
    exterior.setAttribute("aria-pressed", "true");
    exterior.disabled = !viewer?.ready;
    exterior.addEventListener("click", () => {
      viewer.select(building);
      setSceneCopy(building);
      $("#exterior-view")?.setAttribute("aria-pressed", "true");
      $("#interior-view")?.setAttribute("aria-pressed", "false");
      $("#detail-view")?.setAttribute("aria-pressed", "false");
      $("#context-toggle").disabled = false;
      $("#context-toggle").setAttribute("aria-pressed", "false");
      stage.classList.remove("interior-view");
    });
    actions.append(exterior);
    if (building.detailView) {
      const closeup = element("button", "", building.detailView.label);
      closeup.id = "detail-view";
      closeup.setAttribute("aria-pressed", "false");
      closeup.disabled = !viewer?.ready;
      closeup.addEventListener("click", () => {
        viewer.showDetail(building);
        closeup.setAttribute("aria-pressed", "true");
        exterior.setAttribute("aria-pressed", "false");
        $("#interior-view")?.setAttribute("aria-pressed", "false");
        $("#scene-subtitle").textContent = "拖动旋转，近距离观察入口构件";
        $("#view-mode").textContent = building.detailView.label;
        $("#context-toggle").disabled = true;
        $("#context-toggle").setAttribute("aria-pressed", "false");
        stage.classList.remove("interior-view");
      });
      actions.append(closeup);
    }
    if (building.interior) {
      const interior = element("button", "", "公共内部");
      interior.id = "interior-view";
      interior.setAttribute("aria-pressed", "false");
      interior.disabled = !viewer?.ready;
      interior.addEventListener("click", async () => {
        interior.disabled = true;
        delete interior.dataset.failed;
        interior.textContent = "正在加载…";
        try {
          const activated = await viewer.showInterior(building);
          if (!activated || current?.code !== building.code) return;
          interior.setAttribute("aria-pressed", "true");
          exterior.setAttribute("aria-pressed", "false");
          $("#detail-view")?.setAttribute("aria-pressed", "false");
          $("#scene-kicker").textContent = `${building.code} / PUBLIC INTERIOR`;
          $("#scene-subtitle").textContent = "公共空间研究模型，可旋转观察";
          $("#view-mode").textContent = "公共内部";
          $("#context-toggle").disabled = true;
          stage.classList.add("interior-view");
        } catch {
          interior.textContent = "加载失败，重试";
          interior.dataset.failed = "true";
        } finally {
          interior.disabled = false;
          if (!interior.dataset.failed) interior.textContent = "公共内部";
        }
      });
      actions.append(interior);
    }
  }
  if (actions.childElementCount) detailPanel.append(actions);
  if (building.detailedExterior && $("#fallback").hidden) {
    const quality = element("div", "detail-quality");
    const status = element("span", "", "正在准备建筑细节…");
    status.id = "detail-quality-status";
    status.setAttribute("role", "status");
    const retry = element("button", "", "重试加载");
    retry.id = "detail-quality-retry";
    retry.hidden = true;
    retry.addEventListener("click", () => viewer?.retryDetails(building));
    quality.append(status, retry);
    detailPanel.append(quality);
  }
  detailPanel.append(element("p", "detail-description", details.description));
  if (details.images.length > 1) {
    const strip = element("div", "detail-gallery");
    details.images.forEach(([name, caption], index) => {
      const button = element("button");
      button.setAttribute("aria-label", caption);
      const image = element("img");
      image.src = galleryImageUrl(name);
      image.alt = "";
      image.loading = "lazy";
      button.append(image);
      button.addEventListener("click", () =>
        showGallery(details.images, index),
      );
      strip.append(button);
    });
    detailPanel.append(strip);
  }
  const note = element("details", "detail-note");
  note.append(
    element("summary", "", "模型依据与范围"),
    element("p", "", details.note),
  );
  detailPanel.append(note);
  detailPanel.scrollTop = 0;
}

function updateDetailQuality({ code, kind, state }) {
  if (current?.code !== code) return;
  const status = $("#detail-quality-status");
  if (!status) return;
  const subject = kind === "interior" ? "内部细节" : "外观细节";
  status.textContent = state === "ready" ? `${subject}已加载`
    : state === "error" ? "细节加载失败，当前显示基础模型"
    : `正在加载${subject}，可继续浏览…`;
  $("#detail-quality-retry").hidden = state !== "error";
}

function setSceneCopy(building) {
  $("#scene-kicker").textContent = building
    ? `${building.code} / ARCHITECTURE`
    : "LSE CAMPUS";
  $("#scene-title").textContent = building ? building.name : "伦敦的这一角";
  $("#scene-subtitle").textContent = building
    ? building.bounds
      ? "单栋视图，底部可切换周边环境"
      : "尚未建立独立轮廓，保留校园总览"
    : "拖动旋转，点击建筑探索";
  $("#view-mode").textContent = building
    ? building.bounds
      ? "建筑外观"
      : "轮廓待确认"
    : "校园全景";
}

function selectBuilding(code, updateHash = true) {
  if (!code) {
    overview(false, updateHash);
    return;
  }
  const building = buildings.find((item) => item.code === code);
  if (!building) return;
  current = building;
  $("#index-panel").hidden = true;
  detailPanel.hidden = false;
  setSidebar(true);
  sidebar.classList.add("show-detail");
  stage.classList.add("detail-open");
  stage.classList.remove("interior-view");
  $("#context-toggle").disabled = false;
  $("#context-toggle").setAttribute("aria-pressed", "false");
  renderDetail(building);
  setSceneCopy(building);
  viewer?.select(building);
  if (!building.bounds) {
    viewer?.home();
    $("#context-toggle").setAttribute("aria-pressed", "true");
  }
  document.title = `${building.code} ${building.name} — LSEmap`;
  if (updateHash) history.pushState(null, "", `#${building.code}`);
}

function overview(keepIndex = false, updateHash = true) {
  current = null;
  $("#index-panel").hidden = false;
  detailPanel.hidden = true;
  sidebar.classList.remove("show-detail");
  stage.classList.remove("detail-open", "interior-view");
  setSidebar(!mobile.matches || keepIndex);
  $("#context-toggle").disabled = false;
  $("#context-toggle").setAttribute("aria-pressed", "true");
  setSceneCopy(null);
  viewer?.home();
  document.title = "LSEmap — 校园漫游";
  if (updateHash)
    history.pushState(null, "", location.pathname + location.search);
}

function showFailure(message) {
  $("#loading").hidden = true;
  $("#fallback").hidden = false;
  $("#fallback-message").textContent = message;
  for (const id of [
    "zoom-in",
    "zoom-out",
    "north",
    "labels-toggle",
    "context-toggle",
  ])
    $(`#${id}`).disabled = true;
  if (current) renderDetail(current);
}

async function start() {
  const attempt = ++loadAttempt;
  $("#loading").hidden = false;
  $("#loading-copy").textContent = "正在准备校园模型…";
  $("#fallback").hidden = true;
  viewer?.dispose();
  viewer = null;
  try {
    if (!buildings.length) {
      const response = await fetch("/models/catalogue.json", { cache: "no-cache" });
      if (!response.ok) throw new Error("catalogue");
      const data = await response.json();
      modelRevision = data.sourceModelSha256;
      buildings = [...data.buildings].sort(
        (a, b) =>
          Number(b.status === "detailed") - Number(a.status === "detailed") ||
          a.code.localeCompare(b.code),
      );
      renderList();
      const code = decodeURIComponent(location.hash.slice(1));
      if (code) selectBuilding(code, false);
    }
    const { CampusViewer } = await import("./viewer.js");
    if (attempt !== loadAttempt) return;
    viewer = new CampusViewer(
      $("#canvas-container"),
      $("#labels"),
      buildings,
      selectBuilding,
      () =>
        showFailure("浏览器暂停了3D显示。可以重新加载，或继续查看建筑细节图。"),
      updateDetailQuality,
      modelRevision,
    );
    await viewer.load((event) => {
      $("#loading-copy").textContent = event.total
        ? event.loaded >= event.total
          ? "正在整理建筑几何…"
          : `正在加载校园模型 ${Math.round((event.loaded / event.total) * 100)}%`
        : "正在加载校园模型…";
    });
    if (attempt !== loadAttempt) return;
    $("#loading").hidden = true;
    for (const id of [
      "zoom-in",
      "zoom-out",
      "north",
      "labels-toggle",
      "context-toggle",
    ])
      $(`#${id}`).disabled = false;
    viewer.toggleLabels(
      $("#labels-toggle").getAttribute("aria-pressed") === "true",
    );
    viewer.toggleContext(
      $("#context-toggle").getAttribute("aria-pressed") === "true",
    );
    if (current) selectBuilding(current.code, false);
  } catch (error) {
    console.error("Campus viewer could not load:", error);
    showFailure(
      buildings.length
        ? "模型未能加载。请重试，或从建筑目录查看细节图。"
        : "建筑目录未能加载，请检查网络后重试。",
    );
  }
}

$("#building-search").addEventListener("input", renderList);
$("#detail-filter").addEventListener("click", () => {
  detailedOnly = !detailedOnly;
  $("#detail-filter").setAttribute("aria-pressed", String(detailedOnly));
  renderList();
});
$("#index-toggle").addEventListener("click", () => {
  if (current) {
    overview(true);
    return;
  }
  setSidebar(sidebar.classList.contains("closed"));
  if (!sidebar.classList.contains("closed")) $("#building-search").focus();
});
$(".skip-link").addEventListener("click", () => {
  overview(true);
  $("#building-search").focus();
});
$(".brand").addEventListener("click", (event) => {
  event.preventDefault();
  overview();
});
$("#overview").addEventListener("click", () => overview());
$("#zoom-in").addEventListener("click", () => viewer?.zoom(0.78));
$("#zoom-out").addEventListener("click", () => viewer?.zoom(1.28));
$("#north").addEventListener("click", () => viewer?.north());
for (const [id, callback] of [
  ["labels-toggle", (value) => viewer?.toggleLabels(value)],
  ["context-toggle", (value) => viewer?.toggleContext(value)],
]) {
  $(`#${id}`).addEventListener("click", () => {
    const value = $(`#${id}`).getAttribute("aria-pressed") !== "true";
    $(`#${id}`).setAttribute("aria-pressed", String(value));
    callback(value);
  });
}
$("#retry").addEventListener("click", start);
$("#help-open").addEventListener("click", () => $("#help-dialog").showModal());
$("#about-open").addEventListener("click", () =>
  $("#about-dialog").showModal(),
);
for (const dialog of document.querySelectorAll("dialog")) {
  dialog
    .querySelector("[data-close]")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
        dialog.close();
    }
  });
}
$("#gallery-prev").addEventListener("click", () => {
  galleryIndex = (galleryIndex - 1 + gallery.length) % gallery.length;
  renderGallery();
});
$("#gallery-next").addEventListener("click", () => {
  galleryIndex = (galleryIndex + 1) % gallery.length;
  renderGallery();
});
$("#gallery-dialog").addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft") $("#gallery-prev").click();
  if (event.key === "ArrowRight") $("#gallery-next").click();
});
window.addEventListener("popstate", () => {
  const code = decodeURIComponent(location.hash.slice(1));
  if (code) selectBuilding(code, false);
  else overview(false, false);
});
mobile.addEventListener("change", () => {
  if (current) selectBuilding(current.code, false);
  else setSidebar(!mobile.matches);
});
window.addEventListener("pagehide", () => viewer?.dispose());
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    viewer = null;
    startReleaseSync();
    start();
  }
});
setSidebar(!mobile.matches);
start();

startReleaseSync();
