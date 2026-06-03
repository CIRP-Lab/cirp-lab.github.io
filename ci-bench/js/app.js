// Configuration
const CONFIG = {
    PROMPT_MAX_LENGTH: 300,        // Character limit for standard / planner prompt collapse
    EXEC_PROMPT_MAX_LENGTH: 200    // Character limit for execution prompt collapse
};

// State
let leaderboardData = [];
let sortOrder = -1;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadStats();
    await loadLeaderboard();
    await loadComparisons();
    initDragToScroll();
});

// Load Stats
async function loadStats() {
    try {
        const response = await fetch('data/stats.json');
        if (!response.ok) throw new Error('Network response was not ok');
        const stats = await response.json();
        
        const container = document.getElementById('stats-grid');
        for (const [key, value] of Object.entries(stats)) {
            container.innerHTML += `
                <div class="glass p-6 rounded-2xl border border-gray-800 text-center flex flex-col justify-center transform hover:scale-105 transition-transform duration-300">
                    <div class="text-4xl font-bold text-white mb-2">${value}</div>
                    <div class="text-sm font-medium text-gray-400 uppercase tracking-wider">${key}</div>
                </div>
            `;
        }
    } catch (e) {
        console.error("Error loading stats:", e);
    }
}

// Load Leaderboard
async function loadLeaderboard() {
    try {
        const response = await fetch('data/leaderboard.json');
        if (!response.ok) throw new Error('Network response was not ok');
        leaderboardData = await response.json();
        
        leaderboardData.sort((a, b) => (b.Unified - a.Unified));
        renderLeaderboard();
    } catch (e) {
        console.error("Error loading leaderboard:", e);
        document.getElementById('leaderboard-body').innerHTML = `
            <tr><td colspan="9" class="px-6 py-8 text-center text-gray-500">Failed to load leaderboard data.</td></tr>
        `;
    }
}

function renderLeaderboard() {
    const tbody = document.getElementById('leaderboard-body');
    tbody.innerHTML = '';
    
    leaderboardData.forEach((row, index) => {
        let rankClass = "text-gray-400";
        if (index === 0) rankClass = "text-yellow-400 font-bold";
        else if (index === 1) rankClass = "text-gray-300 font-bold";
        else if (index === 2) rankClass = "text-amber-600 font-bold";

        let protocolBadge = '';
        if (row.Protocol === 'P1') {
            protocolBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-800 text-gray-300 border border-gray-700">P1</span>`;
        } else if (row.Protocol === 'P2') {
            protocolBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-900/30 text-brand-400 border border-brand-800">P2</span>`;
        } else if (row.Protocol === 'P3') {
            protocolBadge = `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-900/30 text-purple-400 border border-purple-800">P3</span>`;
        }

        tbody.innerHTML += `
            <tr class="group hover:bg-gray-800/20 transition-colors">
                <td class="px-6 py-4 text-center whitespace-nowrap">${protocolBadge}</td>
                <td class="px-6 py-4 whitespace-nowrap"><div class="font-medium text-gray-200">${row.Model}</div></td>
                <td class="px-6 py-4 whitespace-nowrap text-gray-400 text-sm">${row.Planner}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${row.Type}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right font-semibold ${rankClass}">${row.Unified.toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-gray-400 font-mono text-xs">${row['Ray/Wave Optics'].toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-gray-400 font-mono text-xs">${row['Calibration'].toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-gray-400 font-mono text-xs">${row['Computational Sensing'].toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-gray-400 font-mono text-xs">${row['Image Signal Processing'].toFixed(2)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-right text-gray-400 font-mono text-xs">${row['Inverse Reconstruction'].toFixed(2)}</td>
            </tr>
        `;
    });
}

let currentSortKey = 'Unified';

function sortLeaderboard(key) {
    if (currentSortKey === key) {
        sortOrder *= -1;
    } else {
        currentSortKey = key;
        sortOrder = -1; // Default to descending
    }
    
    leaderboardData.sort((a, b) => {
        return (a[key] - b[key]) * sortOrder;
    });
    renderLeaderboard();
}

// Load Comparisons
async function loadComparisons() {
    try {
        const response = await fetch('data/samples.json');
        if (!response.ok) throw new Error('Network response was not ok');
        const samples = await response.json();
        
        const container = document.getElementById('samples-container');
        container.innerHTML = '';
        
        const models = ['gemini', 'openai', 'qwen'];
        const modelNames = {'gemini': 'Gemini 3.1 Flash Image Preview', 'openai': 'GPT-Image-1.5', 'qwen': 'Qwen-Image-Edit-2511'};
        
        samples.forEach(sample => {
            let protocolsHtml = '';
            
            ['P1', 'P2', 'P3'].forEach(protocol => {
                if (!sample.protocols[protocol]) return;
                const pData = sample.protocols[protocol];
                
                let headerHtml = '';
                if (protocol === 'P1') {
                    const uniqueId = `${sample.task}_${protocol}_prompt`;
                    const isCollapsible = pData.prompt && pData.prompt.length > CONFIG.PROMPT_MAX_LENGTH;
                    headerHtml = `
                        <div class="mb-4">
                            <h3 class="text-xl font-bold text-white mb-4">[ ${protocol} ] Standard</h3>
                            <div class="bg-gray-800/30 px-8 py-4 rounded-lg border-l-4 border-gray-600 relative transition-all duration-200 ${isCollapsible ? 'cursor-pointer hover:bg-gray-800/60' : ''}" ${isCollapsible ? `onclick="toggleText('${uniqueId}')"` : ''}>
                                <p class="text-gray-300 text-sm italic relative z-10 font-serif">
                                    <span class="text-gray-500 text-4xl leading-none absolute -top-2 -left-6">"</span>
                                    ${renderCollapsibleText(pData.prompt, CONFIG.PROMPT_MAX_LENGTH, uniqueId)}
                                    <span class="text-gray-500 text-4xl leading-none absolute -bottom-6 -right-2">"</span>
                                </p>
                            </div>
                        </div>
                    `;
                } else {
                    // P2 / P3
                    const plannerId = `${sample.task}_${protocol}_planner`;
                    const isPlannerCollapsible = pData.planner_prompt && pData.planner_prompt.length > CONFIG.PROMPT_MAX_LENGTH;
                    headerHtml = `
                        <div class="mb-6">
                            <h3 class="text-xl font-bold text-brand-400 mb-4">[ ${protocol} ] Planner-Guided</h3>
                            <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Planner Prompt</h4>
                            <div class="bg-gray-800/30 px-8 py-4 rounded-lg border-l-4 border-brand-600/50 mb-6 relative transition-all duration-200 ${isPlannerCollapsible ? 'cursor-pointer hover:bg-gray-800/60' : ''}" ${isPlannerCollapsible ? `onclick="toggleText('${plannerId}')"` : ''}>
                                <p class="text-gray-300 text-sm italic relative z-10 font-serif">
                                    <span class="text-brand-500/30 text-4xl leading-none absolute -top-2 -left-6">"</span>
                                    ${renderCollapsibleText(pData.planner_prompt, CONFIG.PROMPT_MAX_LENGTH, plannerId)}
                                    <span class="text-brand-500/30 text-4xl leading-none absolute -bottom-6 -right-2">"</span>
                                </p>
                            </div>
                            
                            <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Generated Execution Prompts</h4>
                            <div class="space-y-3 mb-6">
                                ${models.map(m => {
                                    const execId = `${sample.task}_${protocol}_exec_${m}`;
                                    const rawPrompt = pData.prompts[m];
                                    const isExecCollapsible = rawPrompt && rawPrompt.length > CONFIG.EXEC_PROMPT_MAX_LENGTH;
                                    return `
                                    <div class="bg-gray-800/30 p-3 rounded border-l-2 border-brand-500/50 transition-all duration-200 ${isExecCollapsible ? 'cursor-pointer hover:bg-gray-800/60' : ''}" ${isExecCollapsible ? `onclick="toggleText('${execId}')"` : ''}>
                                        <span class="text-[0.65rem] font-bold text-gray-400 uppercase tracking-wider block mb-1">${modelNames[m]}</span>
                                        <div class="text-xs text-gray-300 font-mono">
                                            ${rawPrompt ? renderCollapsibleText(`"${rawPrompt}"`, CONFIG.EXEC_PROMPT_MAX_LENGTH, execId) : '<span class="text-gray-600 italic">No prompt generated</span>'}
                                        </div>
                                    </div>`;
                                }).join('')}
                            </div>
                        </div>
                    `;
                }

                // Results Grid
                let resultsHtml = `
                    <div class="block w-full overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0 scrollbar-thin">
                        <div class="grid grid-cols-5 gap-4 min-w-[768px] md:min-w-0">
                            <div class="text-center font-bold text-gray-400 border-b border-gray-700 pb-2 text-[10px] sm:text-xs uppercase tracking-wider">Input</div>
                            <div class="text-center font-bold text-white border-b border-gray-700 pb-2 text-[10px] sm:text-xs uppercase tracking-wider">GT</div>
                            ${models.map(m => `<div class="text-center font-bold text-gray-200 border-b border-gray-700 pb-2 text-[10px] sm:text-xs leading-tight">${modelNames[m]}</div>`).join('')}
                            
                            <!-- Input Image -->
                            <div class="flex flex-col items-center gap-2">
                                <div class="rounded-lg overflow-hidden border border-gray-700 bg-gray-900 w-full aspect-square flex items-center justify-center">
                                    ${pData.input_url ? `<img src="${pData.input_url}" alt="Input" class="max-w-full max-h-full object-contain" loading="lazy">` : `<span class="text-gray-600">N/A</span>`}
                                </div>
                                <div class="text-center text-gray-500 text-sm mt-2">&nbsp;</div>
                            </div>

                            <!-- GT Image -->
                            <div class="flex flex-col items-center gap-2">
                                <div class="rounded-lg overflow-hidden border border-brand-500 bg-gray-900 w-full aspect-square flex items-center justify-center">
                                    ${pData.gt_url ? `<img src="${pData.gt_url}" alt="GT" class="max-w-full max-h-full object-contain" loading="lazy">` : `<span class="text-gray-600">N/A</span>`}
                                </div>
                                <div class="text-center text-gray-500 text-sm mt-2">&nbsp;</div>
                            </div>
                            
                            <!-- Model Images -->
                            ${models.map(m => {
                                const url = pData.models[m].url;
                                return `
                                <div class="flex flex-col items-center gap-2">
                                    <div class="rounded-lg overflow-hidden border border-gray-800 bg-gray-900/50 w-full aspect-square flex items-center justify-center">
                                        ${url ? `<img src="${url}" alt="${m}" class="max-w-full max-h-full object-contain" loading="lazy">` : `<span class="text-gray-700 text-xs">Missing</span>`}
                                    </div>
                                </div>`;
                            }).join('')}
                            
                            <!-- Scores -->
                            <div class="text-center font-mono font-bold text-gray-500">&nbsp;</div>
                            <div class="text-center font-mono font-bold text-gray-500">&nbsp;</div>
                            ${models.map(m => {
                                const score = pData.models[m].score;
                                const scoreStr = score !== null ? score.toFixed(2) : "N/A";
                                const scoreColor = score !== null ? (score > 80 ? 'text-green-400' : (score > 50 ? 'text-yellow-400' : 'text-red-400')) : 'text-gray-500';
                                return `<div class="text-center font-mono font-bold ${scoreColor}">${scoreStr} <span class="text-[0.6rem] text-gray-500 block uppercase tracking-wide font-sans mt-1">Unified Score</span></div>`;
                            }).join('')}
                        </div>
                    </div>
                `;

                protocolsHtml += `
                    <div class="glass p-6 rounded-2xl border border-gray-800 mb-8 shadow-lg">
                        ${headerHtml}
                        <div class="mt-4">
                            <h4 class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Results</h4>
                            ${resultsHtml}
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML += `
                <div class="mb-16 border border-gray-800 rounded-2xl overflow-hidden shadow-2xl">
                    <div class="bg-gray-900 px-6 py-4 border-b border-gray-800 flex items-center justify-center gap-4">
                        <div class="h-px bg-gray-700 flex-1"></div>
                        <h2 class="text-xl font-bold text-white tracking-widest uppercase">TASK: ${sample.task.replace(/__/g, ' ')}</h2>
                        <div class="h-px bg-gray-700 flex-1"></div>
                    </div>
                    <div class="p-6 bg-gray-950/50">
                        ${protocolsHtml}
                    </div>
                </div>
            `;
        });
        
    } catch (e) {
        console.error("Error loading comparisons:", e);
        document.getElementById('samples-container').innerHTML = `
            <div class="text-center text-gray-500 py-10">Failed to load comparison samples. Check your samples.json</div>
        `;
    }
}

// Collapsible Text Helpers
function renderCollapsibleText(text, maxLength = CONFIG.PROMPT_MAX_LENGTH, uniqueId) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    
    const truncated = text.substring(0, maxLength);
    
    return `
        <span class="collapsible-text-container" id="container-${uniqueId}">
            <span class="truncated-text" id="truncated-${uniqueId}">${truncated}</span>
            <span class="full-text" id="full-${uniqueId}" style="display: none;">${text}</span>
            <button onclick="event.stopPropagation(); toggleText('${uniqueId}')" class="text-brand-400 hover:text-brand-300 font-semibold text-xs ml-1 focus:outline-none" id="btn-${uniqueId}">... Show more</button>
        </span>
    `;
}

window.toggleText = function(uniqueId) {
    // Avoid toggling if the user is highlighting/selecting text
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) return;

    const truncatedSpan = document.getElementById(`truncated-${uniqueId}`);
    const fullSpan = document.getElementById(`full-${uniqueId}`);
    const btn = document.getElementById(`btn-${uniqueId}`);
    
    if (!truncatedSpan || !fullSpan) return;
    
    if (fullSpan.style.display === 'none' || fullSpan.style.display === '') {
        fullSpan.style.display = 'inline';
        truncatedSpan.style.display = 'none';
        if (btn) btn.textContent = 'Show less';
    } else {
        fullSpan.style.display = 'none';
        truncatedSpan.style.display = 'inline';
        if (btn) btn.textContent = '... Show more';
    }
};

// Drag to scroll helper for overflow-x containers
function initDragToScroll() {
    const sliders = document.querySelectorAll('.overflow-x-auto');
    sliders.forEach(slider => {
        let isDown = false;
        let startX;
        let scrollLeft;

        slider.style.cursor = 'grab';
        slider.style.userSelect = 'none';

        slider.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return; // Only drag on left click
            isDown = true;
            slider.style.cursor = 'grabbing';
            startX = e.pageX - slider.offsetLeft;
            scrollLeft = slider.scrollLeft;
        });

        slider.addEventListener('mouseleave', () => {
            isDown = false;
            slider.style.cursor = 'grab';
        });

        slider.addEventListener('mouseup', () => {
            isDown = false;
            slider.style.cursor = 'grab';
        });

        slider.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - slider.offsetLeft;
            const walk = (x - startX) * 1.5;
            slider.scrollLeft = scrollLeft - walk;
        });

        // Prevent default image dragging behavior
        const imgs = slider.querySelectorAll('img');
        imgs.forEach(img => {
            img.addEventListener('dragstart', (e) => {
                e.preventDefault();
            });
            img.style.userSelect = 'none';
        });
    });
}

