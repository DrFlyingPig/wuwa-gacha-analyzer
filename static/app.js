// 全局存储当前玩家 ID
let currentPlayerId = "";

// 简单 Markdown 渲染（加粗、换行）
function renderMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
}

async function analyze() {
    const input = document.getElementById("gachaLink").value.trim();
    const resultDiv = document.getElementById("result");
    const summaryDiv = document.getElementById("summary");
    const btn = document.querySelector(".analyze-btn");

    if (!input) {
        resultDiv.innerHTML = '<div class="error">请输入抽卡链接</div>';
        return;
    }

    btn.disabled = true;
    btn.textContent = "分析中...";
    resultDiv.innerHTML = '<div class="loading">正在获取抽卡记录...</div>';

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ input })
        });

        const data = await response.json();

        if (!data.success) {
            resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }

        currentPlayerId = data.player_id;

        // 显示总结
        summaryDiv.innerHTML = `
            <div class="summary-box">
                <div class="summary-title">📊 抽卡总结</div>
                <div class="summary-content">${renderMarkdown(data.summary)}</div>
                <div class="summary-meta">
                    <span class="total-records">📦 本地共保存 ${data.total_records} 条记录</span>
                    <button class="history-btn" onclick="loadHistory()">📜 查看完整历史</button>
                </div>
            </div>
        `;

        // 显示各卡池结果
        let html = '<div class="pool-tabs">';
        data.results.forEach((r, i) => {
            const activeClass = i === 0 ? "active" : "";
            html += `<div class="pool-tab ${activeClass}" onclick="switchTab(this)" data-pool="${r.pool_type}">${r.pool_name}</div>`;
        });
        html += "</div>";

        data.results.forEach((r, i) => {
            const displayStyle = i === 0 ? "block" : "none";
            html += `<div class="pool-content" id="pool-${r.pool_type}" style="display: ${displayStyle}">`;
            html += renderPoolStats(r);
            html += "</div>";
        });

        resultDiv.innerHTML = html;
    } catch (err) {
        resultDiv.innerHTML = `<div class="error">请求失败: ${err.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.textContent = "开始分析";
    }
}

async function loadHistory() {
    if (!currentPlayerId) {
        alert("请先进行一次抽卡分析");
        return;
    }

    const resultDiv = document.getElementById("result");
    const summaryDiv = document.getElementById("summary");

    resultDiv.innerHTML = '<div class="loading">正在加载历史记录...</div>';

    try {
        const response = await fetch(`/api/history?player_id=${currentPlayerId}`);
        const data = await response.json();

        if (!data.success) {
            resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }

        summaryDiv.innerHTML = `
            <div class="summary-box">
                <div class="summary-title">📜 完整历史记录</div>
                <div class="summary-content">${renderMarkdown(data.summary)}</div>
                <div class="summary-meta">
                    <span class="total-records">📦 本地共保存 ${data.total_records} 条记录</span>
                </div>
            </div>
        `;

        let html = '<div class="pool-tabs">';
        data.results.forEach((r, i) => {
            const activeClass = i === 0 ? "active" : "";
            html += `<div class="pool-tab ${activeClass}" onclick="switchTab(this)" data-pool="${r.pool_type}">${r.pool_name}</div>`;
        });
        html += "</div>";

        data.results.forEach((r, i) => {
            const displayStyle = i === 0 ? "block" : "none";
            html += `<div class="pool-content" id="pool-${r.pool_type}" style="display: ${displayStyle}">`;
            html += renderPoolStats(r);
            html += "</div>";
        });

        resultDiv.innerHTML = html;
    } catch (err) {
        resultDiv.innerHTML = `<div class="error">加载失败: ${err.message}</div>`;
    }
}

function renderPoolStats(r) {
    let html = "";

    // 卡池统计
    html += `
        <div class="pool-stats">
            <div class="stat-item">
                <div class="stat-value">${r.total}</div>
                <div class="stat-label">总抽取次数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${r.five_stars.length}</div>
                <div class="stat-label">5星数量</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${r.four_stars.length}</div>
                <div class="stat-label">4星数量</div>
            </div>
            <div class="stat-item">
                <div class="stat-value ${r.pity_count > 60 ? 'pity-high' : ''}">${r.pity_count}</div>
                <div class="stat-label">当前垫数</div>
            </div>
            <div class="stat-item">
                <div class="stat-value luck-value">${r.luck}</div>
                <div class="stat-label">运气评估</div>
            </div>
        </div>
    `;

    // 50/50 统计（仅角色UP池）
    if (r.pool_type === 1) {
        html += `
            <div class="win-stats">
                <div class="win-title">🎯 50/50 统计</div>
                <div class="win-grid">
                    <div class="win-tag">
                        <span class="win-label">✅ 没歪</span>
                        <span class="win-count win-color">${r.win_count}</span>
                    </div>
                    <div class="win-tag">
                        <span class="win-label">❌ 歪了</span>
                        <span class="win-count lose-color">${r.lose_count}</span>
                    </div>
                    <div class="win-tag">
                        <span class="win-label">📊 胜率</span>
                        <span class="win-count">${r.win_rate}</span>
                    </div>
                </div>
            </div>
        `;
    }

    // 大保底进度条
    const pityPercent = Math.min((r.pity_count / r.pity_limit) * 100, 100);
    html += `
        <div class="pity-section">
            <div class="pity-title">保底进度: ${r.pity_count}/${r.pity_limit}</div>
            <div class="pity-bar">
                <div class="pity-fill" style="width: ${pityPercent}%"></div>
            </div>
        </div>
    `;

    // 5星列表
    html += renderFiveStarList(r.five_stars, r.pool_name);

    // 4星列表
    html += renderFourStarList(r.four_stars);

    return html;
}

function renderFiveStarList(fiveStars, poolName) {
    if (!fiveStars || fiveStars.length === 0) {
        return '<div class="star-section"><div class="star-title">⭐ 5星记录</div><div class="empty">暂无5星记录</div></div>';
    }

    let html = '<div class="star-section"><div class="star-title">⭐ 5星记录</div>';
    html += '<div class="star-list">';

    // 后端已按时间正序排列，这里倒序显示（最新的在前）
    const sorted = [...fiveStars].reverse();
    sorted.forEach((item, index) => {
        let tagHtml = "";
        if (item.won_5050 !== undefined) {
            if (item.won_5050) {
                tagHtml = '<span class="tag tag-won">没歪</span>';
            } else {
                tagHtml = '<span class="tag tag-lost">歪了</span>';
            }
        }

        let iconHtml = "";
        if (item.icon) {
            iconHtml = `<img src="${item.icon}" alt="${item.name}" class="star-item-icon" onerror="this.style.display='none'">`;
        } else {
            iconHtml = `<div class="star-item-icon quality-dot five-star"></div>`;
        }

        html += `
            <div class="star-item">
                ${iconHtml}
                <div class="star-item-info">
                    <div class="star-item-name">${item.name} ${tagHtml}</div>
                    <div class="star-item-time">${item.time} · ${item.pull_number}抽</div>
                </div>
                <div class="star-item-index">#${index + 1}</div>
            </div>
        `;
    });

    html += "</div></div>";
    return html;
}

function renderFourStarList(fourStars) {
    if (!fourStars || fourStars.length === 0) {
        return '<div class="star-section"><div class="star-title">⭐ 4星记录</div><div class="empty">暂无4星记录</div></div>';
    }

    let html = '<div class="star-section"><div class="star-title">⭐ 4星记录 (最近20条)</div>';
    html += '<div class="star-list">';

    // 后端已按时间正序排列，这里倒序显示最新的20条
    const reversed = [...fourStars].reverse();
    const recent = reversed.slice(0, 20);
    recent.forEach(item => {
        let iconHtml = "";
        if (item.icon) {
            iconHtml = `<img src="${item.icon}" alt="${item.name}" class="star-item-icon" onerror="this.style.display='none'">`;
        } else {
            iconHtml = `<div class="star-item-icon quality-dot four-star"></div>`;
        }

        html += `
            <div class="star-item">
                ${iconHtml}
                <div class="star-item-info">
                    <div class="star-item-name">${item.name}</div>
                    <div class="star-item-time">${item.time} · ${item.pull_number}抽</div>
                </div>
            </div>
        `;
    });

    html += "</div></div>";
    return html;
}

function switchTab(tabEl) {
    // 移除所有 active
    document.querySelectorAll(".pool-tab").forEach(t => t.classList.remove("active"));
    tabEl.classList.add("active");

    const poolType = tabEl.dataset.pool;
    document.querySelectorAll(".pool-content").forEach(c => (c.style.display = "none"));
    document.getElementById(`pool-${poolType}`).style.display = "block";
}

function clearInput() {
    document.getElementById("gachaLink").value = "";
}
