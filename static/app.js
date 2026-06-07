/**
 * 鸣潮抽卡分析器 - 前端逻辑
 */

let gachaData = null;
let poolChart = null;
let pityChart = null;

/**
 * 分析抽卡数据
 */
async function analyzeGacha() {
    const urlInput = document.getElementById("gacha-url");
    const btn = document.getElementById("analyze-btn");
    const errorMsg = document.getElementById("error-msg");
    const resultSection = document.getElementById("result-section");

    const url = urlInput.value.trim();
    if (!url) {
        showError("请输入抽卡链接");
        return;
    }

    // 隐藏错误，禁用按钮
    errorMsg.style.display = "none";
    btn.disabled = true;
    btn.querySelector(".btn-text").style.display = "none";
    btn.querySelector(".btn-loading").style.display = "inline";

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });

        const result = await response.json();

        if (!result.success) {
            showError(result.error || "分析失败，请重试");
            return;
        }

        gachaData = result.data;
        renderResults(gachaData);
        resultSection.style.display = "block";

        // 滚动到结果区域
        resultSection.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
        showError("网络错误，请检查后端服务是否启动");
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.querySelector(".btn-text").style.display = "inline";
        btn.querySelector(".btn-loading").style.display = "none";
    }
}

/**
 * 显示错误信息
 */
function showError(msg) {
    const errorMsg = document.getElementById("error-msg");
    errorMsg.textContent = msg;
    errorMsg.style.display = "block";
}

/**
 * 渲染分析结果
 */
function renderResults(data) {
    // 玩家信息
    document.getElementById("player-id").textContent = data.player_info.id;
    document.getElementById("player-server").textContent = data.player_info.server;

    // 总体统计
    document.getElementById("total-pulls").textContent = data.summary.total_pulls;
    document.getElementById("total-five").textContent = data.summary.total_five_stars;
    document.getElementById("total-four").textContent = data.summary.total_four_stars;
    document.getElementById("avg-pulls").textContent = data.summary.avg_five_star_pulls || "-";

    // 默认显示第一个卡池
    const firstPool = Object.keys(data.pools)[0];
    if (firstPool) {
        switchTab(document.querySelector(`.tab[data-pool="${firstPool}"]`));
    }

    // 渲染图表
    renderPoolChart(data.pools);
    renderPityChart(data.pools);
}

/**
 * 切换卡池标签
 */
function switchTab(tabEl) {
    if (!gachaData) return;

    // 更新标签状态
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tabEl.classList.add("active");

    const poolName = tabEl.dataset.pool;
    const pool = gachaData.pools[poolName];

    if (!pool) {
        return;
    }

    // 更新卡池统计
    document.getElementById("pool-total").textContent = pool.total_pulls;
    document.getElementById("pool-pity5").textContent = `${pool.pity_5_count}/80`;
    document.getElementById("pool-pity4").textContent = `${pool.pity_4_count}/10`;
    document.getElementById("pool-avg5").textContent = pool.avg_5star_pulls || "-";

    // 运气评价
    const luckEl = document.getElementById("pool-luck");
    luckEl.textContent = pool.luck_rating;
    luckEl.className = `value luck luck-${pool.luck_rating}`;

    // 保底进度条
    const pityPercent = (pool.pity_5_count / 80) * 100;
    document.getElementById("pity-bar-fill").style.width = `${pityPercent}%`;
    document.getElementById("pity-bar-text").textContent = `${pool.pity_5_count}/80`;

    // 50/50 统计（仅角色UP池显示）
    const section5050 = document.getElementById("pool-5050-section");
    if (poolName === "角色UP" && pool.win_count + pool.lose_count > 0) {
        section5050.style.display = "flex";
        document.getElementById("pool-win").textContent = `${pool.win_count}胜`;
        document.getElementById("pool-lose").textContent = `${pool.lose_count}负`;
        document.getElementById("pool-winrate").textContent = `(${pool.win_rate}%)`;
    } else {
        section5050.style.display = "none";
    }

    // 五星记录列表
    renderFiveStarList(pool.five_stars, poolName);

    // 四星记录列表
    renderFourStarList(pool.four_stars);
}

/**
 * 渲染五星记录列表
 */
function renderFiveStarList(fiveStars, poolName) {
    const container = document.getElementById("five-star-items");

    if (!fiveStars || fiveStars.length === 0) {
        container.innerHTML = '<p class="empty-msg">暂无五星记录</p>';
        return;
    }

    let html = "";
    // 按时间倒序显示
    const sorted = [...fiveStars].reverse();

    sorted.forEach((item) => {
        const isWeapon = item.type === "武器";
        const earlyClass = item.is_early ? "early" : "";
        const earlyTag = item.is_early ? " ✨提前" : "";
        const timeStr = item.time ? formatTime(item.time) : "";

        // 歪/没歪标签（仅角色UP池的角色五星）
        let winLoseTag = "";
        if (poolName === "角色UP" && item.won_5050 !== null && item.won_5050 !== undefined) {
            if (item.won_5050) {
                winLoseTag = '<span class="tag-won">没歪</span>';
            } else {
                winLoseTag = '<span class="tag-lost">歪了</span>';
            }
        }

        // 头像：角色用图片，武器用品质颜色圆圈
        let iconHtml;
        if (item.icon) {
            iconHtml = `<img class="star-item-icon five-star" src="${item.icon}" alt="${item.name}" onerror="this.style.display='none'">`;
        } else {
            iconHtml = `<div class="star-item-icon five-star quality-dot"></div>`;
        }

        html += `
            <div class="star-item ${isWeapon ? "is-weapon" : ""}">
                <div class="star-item-left">
                    ${iconHtml}
                    <span class="star-item-name">${item.name}${winLoseTag}</span>
                </div>
                <div class="star-item-info">
                    <span class="star-item-pity ${earlyClass}">第${item.pity_count}抽出${earlyTag}</span>
                    <span class="star-item-time">${timeStr}</span>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

/**
 * 渲染四星记录列表
 */
function renderFourStarList(fourStars) {
    const container = document.getElementById("four-star-items");

    if (!fourStars || fourStars.length === 0) {
        container.innerHTML = '<p class="empty-msg">暂无四星记录</p>';
        return;
    }

    let html = "";
    const sorted = [...fourStars].reverse();
    // 只显示最近20条四星
    const display = sorted.slice(0, 20);

    display.forEach((item) => {
        const isWeapon = item.type === "武器";
        const timeStr = item.time ? formatTime(item.time) : "";

        // 头像：角色用图片，武器用品质颜色圆圈
        let iconHtml;
        if (item.icon) {
            iconHtml = `<img class="star-item-icon four-star" src="${item.icon}" alt="${item.name}" onerror="this.style.display='none'">`;
        } else {
            iconHtml = `<div class="star-item-icon four-star quality-dot"></div>`;
        }

        html += `
            <div class="star-item ${isWeapon ? "is-weapon" : ""}" style="border-left-color:var(--four-star)">
                <div class="star-item-left">
                    ${iconHtml}
                    <span class="star-item-name">${item.name}</span>
                </div>
                <div class="star-item-info">
                    <span class="star-item-pity">第${item.pity_count}抽出</span>
                    <span class="star-item-time">${timeStr}</span>
                </div>
            </div>
        `;
    });

    if (fourStars.length > 20) {
        html += `<p class="empty-msg">仅显示最近20条四星记录（共${fourStars.length}条）</p>`;
    }

    container.innerHTML = html;
}

/**
 * 格式化时间
 */
function formatTime(timeStr) {
    try {
        const date = new Date(timeStr);
        return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, "0")}`;
    } catch {
        return timeStr;
    }
}

/**
 * 渲染卡池分布饼图
 */
function renderPoolChart(pools) {
    const ctx = document.getElementById("pool-chart").getContext("2d");

    // 销毁旧图表
    if (poolChart) {
        poolChart.destroy();
    }

    const labels = [];
    const values = [];
    const colors = ["#6c5ce7", "#a29bfe", "#ff6b6b", "#fdcb6e"];

    Object.entries(pools).forEach(([name, pool]) => {
        if (pool.total_pulls > 0) {
            labels.push(name);
            values.push(pool.total_pulls);
        }
    });

    if (values.length === 0) {
        return;
    }

    poolChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [
                {
                    data: values,
                    backgroundColor: colors.slice(0, labels.length),
                    borderWidth: 0,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#e0e0e0",
                        padding: 16,
                        font: { size: 13 },
                    },
                },
            },
        },
    });
}

/**
 * 渲染五星出货抽数分布图
 */
function renderPityChart(pools) {
    const ctx = document.getElementById("pity-chart").getContext("2d");

    // 销毁旧图表
    if (pityChart) {
        pityChart.destroy();
    }

    // 收集所有五星的出货抽数
    const allPities = [];
    Object.values(pools).forEach((pool) => {
        pool.five_stars.forEach((f) => {
            allPities.push(f.pity_count);
        });
    });

    if (allPities.length === 0) {
        return;
    }

    // 按抽数范围分组
    const ranges = ["1-20", "21-40", "41-60", "61-70", "71-80"];
    const counts = [0, 0, 0, 0, 0];

    allPities.forEach((p) => {
        if (p <= 20) counts[0]++;
        else if (p <= 40) counts[1]++;
        else if (p <= 60) counts[2]++;
        else if (p <= 70) counts[3]++;
        else counts[4]++;
    });

    pityChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ranges,
            datasets: [
                {
                    label: "出货次数",
                    data: counts,
                    backgroundColor: [
                        "rgba(0, 184, 148, 0.7)",
                        "rgba(108, 92, 231, 0.7)",
                        "rgba(253, 203, 110, 0.7)",
                        "rgba(225, 112, 85, 0.7)",
                        "rgba(255, 107, 107, 0.7)",
                    ],
                    borderWidth: 0,
                    borderRadius: 6,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    ticks: { color: "#888" },
                    grid: { color: "rgba(255,255,255,0.05)" },
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: "#888",
                        stepSize: 1,
                    },
                    grid: { color: "rgba(255,255,255,0.05)" },
                },
            },
        },
    });
}

// 回车键触发分析
document.getElementById("gacha-url").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        analyzeGacha();
    }
});
