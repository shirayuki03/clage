const canvas = root.querySelector("canvas");
const ctx = canvas.getContext("2d");
const modeButtons = root.querySelectorAll("[data-clage-mode]");
const addCostumeButton = root.querySelector("[data-clage-add-costume]");
const costumeInput = root.querySelector("[data-clage-costume-input]");
const costumeList = root.querySelector("[data-clage-costume-list]");
const images = new Map();
let latestSprites = {};
let costumes = api.getCostumes();
let renderPending = false;

canvas.tabIndex = 0;
canvas.addEventListener("pointerdown", () => canvas.focus({ preventScroll: true }));

function setModeButtonState(mode) {
  modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.clageMode === mode);
  });
}

function renderCostumes() {
  if (!costumeList) return;
  costumeList.innerHTML = "";
  if (!costumes.length) {
    const empty = document.createElement("p");
    empty.className = "clage-costume-empty";
    empty.textContent = "画像を追加すると、costume文でファイル名だけを使えます。";
    costumeList.appendChild(empty);
    return;
  }

  costumes.forEach((costume) => {
    const item = document.createElement("article");
    item.className = "clage-costume-item";
    item.innerHTML = `
      <div class="clage-costume-preview"><img alt="" src="${costume.url}"></div>
      <div class="clage-costume-meta">
        <div class="clage-costume-name" title="${costume.name}">${costume.name}</div>
        <div class="clage-costume-actions"></div>
      </div>
    `;
    const actions = item.querySelector(".clage-costume-actions");
    const copyButton = document.createElement("button");
    copyButton.type = "button";
    copyButton.textContent = "コピー";
    copyButton.addEventListener("click", () => api.copyCostumeReference(costume.name));
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "削除";
    removeButton.addEventListener("click", () => api.removeCostume(costume.name));
    actions.append(copyButton, removeButton);
    costumeList.appendChild(item);
  });
}

function assetFor(costume) {
  if (!costume) return null;
  const name = String(costume).split("/").filter(Boolean).pop();
  return extension.assets[costume] || extension.assets[name] || null;
}

function loadImage(src) {
  if (!src) return null;
  if (images.has(src)) return images.get(src);
  const img = new Image();
  img.src = src;
  images.set(src, img);
  img.addEventListener("load", render);
  return img;
}

function fallbackColor(name) {
  const colors = ["#2f73ff", "#20a67a", "#f46d5e", "#f3a712", "#8b5cf6"];
  let hash = 0;
  for (const char of String(name)) {
    hash = (hash + char.charCodeAt(0)) % colors.length;
  }
  return colors[hash];
}

function drawSprite(name, sprite) {
  if (!sprite.visible) return;
  const x = canvas.width / 2 + Number(sprite.x || 0);
  const y = canvas.height / 2 - Number(sprite.y || 0);
  const direction = Number(sprite.direction || 90);
  const img = loadImage(assetFor(sprite.costume));

  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(((90 - direction) * Math.PI) / 180);
  if (img && img.complete && img.naturalWidth > 0) {
    ctx.drawImage(img, -img.width / 2, -img.height / 2);
  } else {
    ctx.fillStyle = fallbackColor(name);
    ctx.fillRect(-22, -22, 44, 44);
    ctx.fillStyle = "#fff";
    ctx.font = "12px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(String(name).slice(0, 6), 0, 4);
  }
  ctx.restore();
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  Object.entries(latestSprites).forEach(([name, sprite]) => drawSprite(name, sprite));
}

function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(() => {
    renderPending = false;
    render();
  });
}

modeButtons.forEach((button) => {
  button.addEventListener("click", () => api.setEditMode(button.dataset.clageMode));
});

addCostumeButton?.addEventListener("click", () => costumeInput.click());
costumeInput?.addEventListener("change", () => {
  const result = api.addCostumes(costumeInput.files);
  costumes = result.costumes || costumes;
  costumeInput.value = "";
  renderCostumes();
});

api.onEvent((eventType, payload) => {
  if (eventType === "assets") {
    render();
    return;
  }
  if (eventType === "costumes") {
    costumes = payload.costumes || [];
    renderCostumes();
    return;
  }
  if (eventType === "mode") {
    setModeButtonState(payload.mode);
    return;
  }
  if (eventType !== "state") return;
  latestSprites = payload.sprites || {};
  scheduleRender();
});

setModeButtonState("code");
renderCostumes();
render();
