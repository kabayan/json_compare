// グローバル変数
let currentMode = 'single';
let currentPollingInterval = null;
let currentTaskId = null;
let pollingErrorCount = 0;
const maxPollingErrors = 5;
let fullApiResponse = null;

// DOMが読み込まれたら初期化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    switchMode('single');
});

// イベントリスナーの初期化
function initializeEventListeners() {
    // フォーム要素の取得
    const form = document.getElementById('uploadForm');
    const dualForm = document.getElementById('dualForm');
    const fileInput = document.getElementById('file');
    const fileLabel = document.getElementById('fileLabel');
    const file1Input = document.getElementById('file1');
    const file1Label = document.getElementById('file1Label');
    const file2Input = document.getElementById('file2');
    const file2Label = document.getElementById('file2Label');

    // ファイル選択イベント
    fileInput.addEventListener('change', function() {
        updateFileLabel(this, fileLabel, '📁 クリックしてファイルを選択（.jsonl）');
    });

    file1Input.addEventListener('change', function() {
        updateFileLabel(this, file1Label, '📁 1つ目のファイル（.jsonl）');
    });

    file2Input.addEventListener('change', function() {
        updateFileLabel(this, file2Label, '📁 2つ目のファイル（.jsonl）');
    });

    // フォーム送信イベント
    form.addEventListener('submit', handleSingleFileSubmit);
    dualForm.addEventListener('submit', handleDualFileSubmit);
}

// ファイルラベルの更新
function updateFileLabel(input, label, defaultText) {
    if (input.files && input.files.length > 0) {
        const fileName = input.files[0].name;
        label.textContent = `✅ ${fileName}`;
        label.classList.add('file-selected');
    } else {
        label.textContent = defaultText;
        label.classList.remove('file-selected');
    }
}

// モード切り替え
function switchMode(mode) {
    currentMode = mode;

    // タブボタンのアクティブ状態を更新
    document.querySelectorAll('.tab-button').forEach(btn => {
        if (btn.dataset.mode === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // フォームの表示切り替え
    document.querySelectorAll('.mode-form').forEach(form => {
        if (form.dataset.mode === mode) {
            form.classList.add('active');
        } else {
            form.classList.remove('active');
        }
    });

    // 結果をクリア
    hideResults();
}

// LLM設定の表示/非表示切り替え（単一ファイル用）
function toggleLLMConfig() {
    const useLLMCheckbox = document.getElementById('use_llm');
    const llmConfigSection = document.getElementById('llm_config_section');

    if (useLLMCheckbox.checked) {
        llmConfigSection.classList.add('active');
    } else {
        llmConfigSection.classList.remove('active');
    }
}

// LLM設定の表示/非表示切り替え（2ファイル用）
function toggleDualLLMConfig() {
    const useLLMCheckbox = document.getElementById('dual_use_llm');
    const llmConfigSection = document.getElementById('dual_llm_config_section');

    if (useLLMCheckbox.checked) {
        llmConfigSection.classList.add('active');
    } else {
        llmConfigSection.classList.remove('active');
    }
}

// 単一ファイル送信処理
function handleSingleFileSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    submitFormData('/api/compare/async', formData);
}

// 2ファイル送信処理
function handleDualFileSubmit(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    submitFormData('/api/compare/dual/async', formData);
}

// フォームデータ送信
async function submitFormData(endpoint, formData) {
    try {
        showLoading();
        hideResults();
        clearMessages();

        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'サーバーエラーが発生しました');
        }

        if (data.task_id) {
            // 非同期処理開始 - ポーリング開始
            startPolling(data.task_id);
            showProgress();
        } else if (data.result || data.file || data.score !== undefined) {
            // 同期処理完了 - 直接結果表示
            hideLoading();
            displayResults(data);
        } else {
            throw new Error('予期しないレスポンス形式です');
        }
    } catch (error) {
        console.error('Submission error:', error);
        hideLoading();
        hideProgress();
        showError(error.message);
    }
}

// ポーリング開始
function startPolling(taskId) {
    if (currentPollingInterval) {
        stopPolling();
    }

    currentTaskId = taskId;
    pollingErrorCount = 0;

    currentPollingInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/progress/${taskId}`);

            if (!response.ok) {
                if (response.status === 404) {
                    console.error('Task not found:', taskId);
                    stopPolling();
                    showError('タスクが見つかりません');
                    return;
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // 進捗更新
            updateProgress(data);

            // エラー状態の場合
            if (data.status === 'error') {
                stopPolling();
                hideProgress();
                showError(data.error_message || 'エラーが発生しました');
            }
            // 完了状態の場合
            else if (data.status === 'completed') {
                stopPolling();
                hideProgress();
                hideLoading();

                // 結果表示
                if (data.result) {
                    displayResults(data);
                } else {
                    showSuccess('処理が完了しました');
                }
            }

            // エラーカウンターをリセット
            pollingErrorCount = 0;

        } catch (error) {
            console.error('Polling error:', error);
            pollingErrorCount++;

            // 最大エラー数を超えた場合は停止
            if (pollingErrorCount >= maxPollingErrors) {
                stopPolling();
                hideProgress();
                showError(`接続エラーが続いたため、処理を停止しました (${pollingErrorCount}回連続失敗)`);
            }
        }
    }, 1000); // 1秒間隔

    console.log(`Started polling for task: ${taskId}`);
}

// ポーリング停止
function stopPolling() {
    if (currentPollingInterval) {
        clearInterval(currentPollingInterval);
        currentPollingInterval = null;
        console.log('Stopped polling');
    }
    currentTaskId = null;
}

// 進捗更新
function updateProgress(data) {
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressCurrent = document.getElementById('progressCurrent');
    const progressTotal = document.getElementById('progressTotal');
    const elapsedTime = document.getElementById('elapsedTime');
    const remainingTime = document.getElementById('remainingTime');
    const processingSpeed = document.getElementById('processingSpeed');

    if (progressContainer && data) {
        // 進捗バーの更新
        const percentage = data.percentage || 0;
        progressFill.style.width = `${percentage}%`;
        progressFill.textContent = `${Math.round(percentage)}%`;

        // 進捗情報の更新
        if (progressCurrent) progressCurrent.textContent = data.current || 0;
        if (progressTotal) progressTotal.textContent = data.total || 0;

        // 経過時間の更新
        if (elapsedTime && data.elapsed_seconds) {
            const minutes = Math.floor(data.elapsed_seconds / 60);
            const seconds = Math.floor(data.elapsed_seconds % 60);
            elapsedTime.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }

        // 残り時間の更新
        if (remainingTime && data.estimated_remaining_seconds !== undefined) {
            if (data.estimated_remaining_seconds <= 0) {
                remainingTime.textContent = 'まもなく完了';
            } else if (data.estimated_remaining_seconds < 60) {
                remainingTime.textContent = `約${Math.ceil(data.estimated_remaining_seconds)}秒`;
            } else {
                const remMinutes = Math.floor(data.estimated_remaining_seconds / 60);
                const remSeconds = Math.floor(data.estimated_remaining_seconds % 60);
                remainingTime.textContent = `約${remMinutes}分${remSeconds}秒`;
            }
        }

        // 処理速度の更新
        if (processingSpeed && data.processing_speed) {
            processingSpeed.textContent = `${data.processing_speed.toFixed(1)}`;
        }
    }
}

// 結果表示
function displayResults(data) {
    hideLoading();
    hideProgress();

    // 既存の結果セクションを削除
    const existingResults = document.querySelectorAll('[id*="result"], [id*="complete-results"]');
    existingResults.forEach(el => el.remove());

    // APIレスポンス全体を保存
    fullApiResponse = data.result || data;

    // 結果セクションを作成
    const resultDiv = document.createElement('div');
    resultDiv.id = 'resultContainer';
    resultDiv.className = 'result-container active';

    let displayData = fullApiResponse;
    let isTruncated = false;

    // 配列形式（ファイル出力）の場合は最初の20行のみ表示
    if (Array.isArray(fullApiResponse) && fullApiResponse.length > 20) {
        displayData = fullApiResponse.slice(0, 20);
        isTruncated = true;
    }

    // JSONを整形して表示
    const jsonString = JSON.stringify(displayData, null, 2);

    resultDiv.innerHTML = `
        <h3 style="color: #28a745; margin-bottom: 15px;">✅ 処理完了</h3>

        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">
            <h4>📋 APIレスポンス</h4>
            ${isTruncated ? '<p style="color: #856404; background: #fff3cd; padding: 10px; border-radius: 4px;">⚠️ ファイル形式: 先頭20行のみ表示中（全' + fullApiResponse.length + '行）</p>' : ''}

            <pre id="jsonDisplay" style="background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; max-height: 600px; overflow-y: auto; font-family: monospace; font-size: 12px; line-height: 1.5;"></pre>
        </div>

        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0; display: flex; gap: 10px;">
            <button id="downloadJsonBtn" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
                📥 JSON形式でダウンロード${isTruncated ? '（全件）' : ''}
            </button>
            ${Array.isArray(fullApiResponse) ? `
            <button id="downloadJsonlBtn" style="padding: 10px 20px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
                📥 JSONL形式でダウンロード${isTruncated ? '（全件）' : ''}
            </button>
            ` : ''}
        </div>
    `;

    // JSONを安全に表示
    const jsonDisplay = resultDiv.querySelector('#jsonDisplay');
    if (jsonDisplay) {
        jsonDisplay.textContent = jsonString;
    }

    // ダウンロードボタンのイベントリスナーを設定
    const jsonBtn = resultDiv.querySelector('#downloadJsonBtn');
    if (jsonBtn) {
        jsonBtn.addEventListener('click', () => downloadResult('json'));
    }
    const jsonlBtn = resultDiv.querySelector('#downloadJsonlBtn');
    if (jsonlBtn) {
        jsonlBtn.addEventListener('click', () => downloadResult('jsonl'));
    }

    // 結果をページに挿入
    const container = document.querySelector('.container');
    container.appendChild(resultDiv);

    console.log('Results displayed successfully:', fullApiResponse);
}

// ダウンロード関数
function downloadResult(format) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    let filename, content, mimeType;

    if (format === 'jsonl' && Array.isArray(fullApiResponse)) {
        // JSONL形式（ファイル形式の場合）
        filename = `result_${timestamp}.jsonl`;
        content = fullApiResponse.map(item => JSON.stringify(item)).join('\n');
        mimeType = 'application/x-jsonlines';
    } else {
        // JSON形式（すべてのケース）
        filename = `result_${timestamp}.json`;
        content = JSON.stringify(fullApiResponse, null, 2);
        mimeType = 'application/json';
    }

    // Blobを作成してダウンロード
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // ダウンロード完了の通知
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '✅ ダウンロード完了';
    btn.style.background = '#198754';
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = format === 'jsonl' ? '#17a2b8' : '#28a745';
    }, 2000);
}

// UI表示制御関数
function showLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.classList.add('active');
}

function hideLoading() {
    const loading = document.getElementById('loading');
    if (loading) loading.classList.remove('active');
}

function showProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) progressContainer.classList.add('active');
}

function hideProgress() {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) progressContainer.classList.remove('active');
}

function showResults() {
    const resultContainer = document.getElementById('resultContainer');
    if (resultContainer) resultContainer.classList.add('active');
}

function hideResults() {
    const resultContainer = document.getElementById('resultContainer');
    if (resultContainer) resultContainer.classList.remove('active');

    // 動的に作成された結果セクションも削除
    const existingResults = document.querySelectorAll('[id*="result"], [id*="complete-results"]');
    existingResults.forEach(el => el.remove());
}

function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    if (errorMessage) {
        errorMessage.textContent = message;
        errorMessage.classList.add('active');
        setTimeout(() => {
            errorMessage.classList.remove('active');
        }, 5000);
    }
}

function showSuccess(message) {
    const successMessage = document.getElementById('successMessage');
    if (successMessage) {
        successMessage.textContent = message;
        successMessage.classList.add('active');
        setTimeout(() => {
            successMessage.classList.remove('active');
        }, 3000);
    }
}

function clearMessages() {
    const errorMessage = document.getElementById('errorMessage');
    const successMessage = document.getElementById('successMessage');

    if (errorMessage) errorMessage.classList.remove('active');
    if (successMessage) successMessage.classList.remove('active');
}