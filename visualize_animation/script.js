// HTML要素を取得
const slider = document.getElementById('timeSlider');
const imageElement = document.getElementById('simulationImage');
const frameDisplay = document.getElementById('frameNumber');

// 総フレーム数
const totalFrames = parseInt(slider.max);

// スライダーの値が変更されたときの処理
slider.addEventListener('input', function() {
    // 1. スライダーの現在の値 (フレーム番号) を取得
    const frameIndex = parseInt(this.value);
    
    // 2. フレーム番号をゼロパディングしてファイル名を作成
    // 例: 1 -> "001", 10 -> "010" （ここでは3桁を想定）
    const paddedIndex = String(frameIndex).padStart(3, '0');
    
    // 3. 画像のパスを更新
    const imagePath = `../frames/frame_${paddedIndex}.png`;
    imageElement.src = imagePath;
    
    // 4. 現在のフレーム数を表示を更新
    frameDisplay.textContent = frameIndex;
});

// 初期表示
frameDisplay.textContent = slider.value;