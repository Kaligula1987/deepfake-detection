// web/static/script.js
class DeepfakeDetector {
    constructor() {
        this.initializeEventListeners();
        this.checkUserStatus();
    }

    initializeEventListeners() {
        const uploadBox = document.getElementById('uploadBox');
        const fileInput = document.getElementById('fileInput');
        const analyzeBtn = document.getElementById('analyzeBtn');

        uploadBox.addEventListener('click', () => fileInput.click());
        uploadBox.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadBox.addEventListener('drop', (e) => this.handleDrop(e));
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
    }

    handleDragOver(e) {
        e.preventDefault();
        e.currentTarget.style.background = '#f0f8ff';
        e.currentTarget.style.borderColor = '#4CAF50';
    }

    handleDrop(e) {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.processFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.processFile(file);
        }
    }

    async processFile(file) {
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }

        // Show preview
        this.showPreview(file);
        
        // Analyze image
        await this.analyzeImage(file);
    }

    showPreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('imagePreview').innerHTML = `
                <img src="${e.target.result}" alt="Preview" style="max-width: 300px; border-radius: 10px;">
            `;
            document.getElementById('analyzeBtn').style.display = 'block';
        };
        reader.readAsDataURL(file);
    }

    async analyzeImage(file) {
        this.showLoading();
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/predict/', {
                method: 'POST',
                body: formData
            });

            if (response.status === 429) {
                const error = await response.json();
                this.showLimitReached(error);
                return;
            }

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const result = await response.json();
            this.showResult(result);
            
        } catch (error) {
            this.showError('Analysis failed. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    showLoading() {
        document.getElementById('uploadArea').style.display = 'none';
        document.getElementById('loadingArea').style.display = 'block';
    }

    hideLoading() {
        document.getElementById('loadingArea').style.display = 'none';
    }

    showResult(result) {
        const resultArea = document.getElementById('resultArea');
        const resultDiv = document.getElementById('result');
        
        const confidencePercent = Math.round(result.result.confidence * 100);
        
        resultDiv.innerHTML = `
            <div class="result-header">
                <h2>Analysis Result</h2>
                <div class="confidence-score">
                    <h3 style="color: ${this.getColorForLabel(result.result.final_label)}">
                        ${result.result.final_label}
                    </h3>
                    <p>Confidence: ${confidencePercent}%</p>
                </div>
            </div>
            
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${confidencePercent}%"></div>
            </div>
            
            <div class="result-details">
                <div class="detail-item">
                    <strong>AI Generation Score:</strong> ${(result.result.ai_score * 100).toFixed(1)}%
                </div>
                <div class="detail-item">
                    <strong>Manipulation Score:</strong> ${(result.result.manipulation_score * 100).toFixed(1)}%
                </div>
                <div class="detail-item">
                    <strong>Faces Detected:</strong> ${result.result.faces_detected}
                </div>
            </div>
            
            ${result.user_type === 'free' ? `
                <div class="premium-banner">
                    <h4>🔒 Free Scan Used</h4>
                    <p>You've used your free scan for today. Upgrade to Premium for unlimited scans!</p>
                    <button onclick="window.location.href='/premium'" class="btn">
                        Upgrade to Premium - €9.99/month
                    </button>
                </div>
            ` : ''}
            
            <div style="text-align: center; margin-top: 20px;">
                <button onclick="this.resetApp()" class="btn">Analyze Another Image</button>
            </div>
        `;
        
        resultArea.style.display = 'block';
    }

    showLimitReached(error) {
        const resultArea = document.getElementById('resultArea');
        const resultDiv = document.getElementById('result');
        
        resultDiv.innerHTML = `
            <div class="premium-banner">
                <h2>🔒 Daily Limit Reached</h2>
                <p>${error.message}</p>
                <p>Upgrade to Premium for unlimited deepfake detection scans!</p>
                <button onclick="window.location.href='/premium'" class="btn">
                    Upgrade to Premium - €9.99/month
                </button>
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <button onclick="this.resetApp()" class="btn">Try Again Tomorrow</button>
            </div>
        `;
        
        resultArea.style.display = 'block';
        this.hideLoading();
    }

    showError(message) {
        alert(message);
        this.resetApp();
    }

    resetApp() {
        document.getElementById('uploadArea').style.display = 'block';
        document.getElementById('resultArea').style.display = 'none';
        document.getElementById('imagePreview').innerHTML = '';
        document.getElementById('fileInput').value = '';
        document.getElementById('analyzeBtn').style.display = 'none';
    }

    getColorForLabel(label) {
        const colors = {
            'Likely Real': '#4CAF50',
            'AI-generated': '#FF9800',
            'Manipulated/Edited': '#F44336',
            'Deepfake': '#9C27B0'
        };
        return colors[label] || '#666';
    }

    async checkUserStatus() {
        try {
            const response = await fetch('/api/user/status');
            const status = await response.json();
            
            // Show free scans remaining
            if (status.scan_status.user_type === 'free') {
                const scanInfo = document.getElementById('scanInfo');
                if (scanInfo) {
                    scanInfo.innerHTML = `Free scans today: ${status.scan_status.scans_left}/1`;
                }
            }
        } catch (error) {
            console.log('Could not fetch user status');
        }
    }
}

// Initialize the app when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.detector = new DeepfakeDetector();
});
