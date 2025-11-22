// web/static/script.js
let currentFile = null;
let userStatus = null;

// Load user status on page load
async function loadUserStatus() {
    try {
        const response = await fetch('/api/user/status');
        userStatus = await response.json();
        updateUIWithUserStatus();
    } catch (error) {
        console.error('Error loading user status:', error);
        // Default to free user if API fails
        userStatus = {
            scan_status: {
                user_type: 'free',
                scans_left: 1,
                scans_used: 0
            }
        };
        updateUIWithUserStatus();
    }
}

function updateUIWithUserStatus() {
    const uploadBox = document.getElementById('uploadBox');
    
    if (!uploadBox) return;
    
    if (userStatus.scan_status.user_type === 'premium') {
        uploadBox.innerHTML = `
            <div class="upload-icon">🚀</div>
            <h3>Premium User - Unlimited Scans</h3>
            <p>You have unlimited deepfake detection scans</p>
            <input type="file" id="fileInput" accept="image/*" hidden>
            <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                Analyze Image
            </button>
        `;
        setupFileInput();
    } else {
        const scansLeft = userStatus.scan_status.scans_left || 0;
        const scansUsed = userStatus.scan_status.scans_used || 0;
        
        if (scansLeft > 0) {
            uploadBox.innerHTML = `
                <div class="upload-icon">📁</div>
                <h3>Free Scan Available</h3>
                <p>You have ${scansLeft} free scan(s) remaining today</p>
                <p class="scan-counter">Used: ${scansUsed}/1 today</p>
                <input type="file" id="fileInput" accept="image/*" hidden>
                <button class="upload-btn" onclick="document.getElementById('fileInput').click()">
                    Use Free Scan
                </button>
                <button class="premium-btn" onclick="showUpgradePrompt()" style="margin-top: 10px;">
                    🔓 Upgrade to Unlimited
                </button>
            `;
            setupFileInput();
        } else {
            uploadBox.innerHTML = `
                <div class="upload-icon">⏰</div>
                <h3>Daily Limit Reached</h3>
                <p>You've used all your free scans for today</p>
                <p class="scan-counter">Used: ${scansUsed}/1 today</p>
                <div style="margin: 20px 0;">
                    <button class="premium-btn" onclick="showUpgradePrompt()">
                        🚀 Upgrade to Premium
                    </button>
                </div>
                <p><small>Free scans reset at midnight</small></p>
                <button class="upload-btn" onclick="window.location.href='/premium'" style="margin-top: 10px;">
                    Learn About Premium Features
                </button>
            `;
            // No file input when limit reached
        }
    }
}

function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileInputChange);
    }
}

function showUpgradePrompt() {
    if (confirm('🚀 Upgrade to Premium!\n\nGet unlimited deepfake detection scans for just €5/month!\n\nClick OK to learn more about premium features.')) {
        window.location.href = '/premium';
    }
}

// File input handler
function handleFileInputChange(e) {
    const file = e.target.files[0];
    if (file) {
        handleFileSelect(file);
    }
}

function handleFileSelect(file) {
    // Validate file type
    if (!file.type.startsWith('image/')) {
        showError('Please select a valid image file (JPG, PNG, WebP)');
        return;
    }

    // Validate file size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showError('File too large. Please select an image under 10MB.');
        return;
    }

    // Check if user can scan (for free users)
    if (userStatus.scan_status.user_type === 'free') {
        const scansLeft = userStatus.scan_status.scans_left || 0;
        if (scansLeft <= 0) {
            showError('You have no free scans remaining today. Please upgrade to premium for unlimited scans.');
            const fileInput = document.getElementById('fileInput');
            if (fileInput) fileInput.value = '';
            return;
        }
    }

    currentFile = file;
    
    // Show preview
    const preview = document.getElementById('preview');
    const previewSection = document.getElementById('previewSection');
    
    if (preview && previewSection) {
        preview.src = URL.createObjectURL(file);
        previewSection.style.display = 'block';
        
        // Hide other sections
        hideAllSections();
        previewSection.style.display = 'block';
    }
}

async function analyzeImage() {
    if (!currentFile) {
        showError('Please select an image first');
        return;
    }

    // Double-check free user limits
    if (userStatus.scan_status.user_type === 'free') {
        const scansLeft = userStatus.scan_status.scans_left || 0;
        if (scansLeft <= 0) {
            showError('You have no free scans remaining today. Please upgrade to premium for unlimited scans.');
            return;
        }
    }

    hideAllSections();
    const loadingSection = document.getElementById('loadingSection');
    if (loadingSection) loadingSection.style.display = 'block';

    const formData = new FormData();
    formData.append("file", currentFile);

    try {
        const response = await fetch("/predict/", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            
            // Handle rate limit errors
            if (response.status === 429) {
                showUpgradeLimitReached(errorData);
                return;
            }
            
            throw new Error(errorData.detail || `Server error: ${response.status}`);
        }

        const data = await response.json();
        
        // Update user status after successful scan
        if (data.scan_info) {
            userStatus.scan_status.scans_used = data.scan_info.scans_used_today;
            userStatus.scan_status.scans_left = data.scan_info.scans_left_today;
            updateUIWithUserStatus();
        }
        
        displayResults(data);

    } catch (err) {
        showError(err.message);
    }
}

function showUpgradeLimitReached(errorData) {
    hideAllSections();
    
    const errorSection = document.getElementById('errorSection');
    const errorText = document.getElementById('errorText');
    
    if (errorSection && errorText) {
        errorText.innerHTML = `
            <h4>🎯 Daily Limit Reached</h4>
            <p>You've used your free scan for today!</p>
            <p><strong>Scans used today:</strong> ${errorData.scans_used}/1</p>
            <div style="margin: 20px 0;">
                <button class="premium-btn" onclick="window.location.href='/premium'" style="font-size: 1.2em; padding: 15px 30px;">
                    🚀 Upgrade to Premium - €5/month
                </button>
            </div>
            <p><small>Free scans reset: ${errorData.next_free_scan || 'tomorrow'}</small></p>
        `;
        
        errorSection.style.display = 'block';
    }
}

function displayResults(data) {
    const result = data.result;
    
    // Update final label and confidence
    const finalLabel = document.getElementById('finalLabel');
    const confidence = document.getElementById('confidence');
    
    if (finalLabel && confidence) {
        finalLabel.textContent = result.final_label;
        finalLabel.setAttribute('data-label', result.final_label);
        confidence.textContent = `${Math.round(result.confidence * 100)}%`;
    }
    
    // Update scores
    const aiScore = document.getElementById('aiScore');
    const manipScore = document.getElementById('manipScore');
    const aiScoreBar = document.getElementById('aiScoreBar');
    const manipScoreBar = document.getElementById('manipScoreBar');
    
    if (aiScore && manipScore && aiScoreBar && manipScoreBar) {
        aiScore.textContent = result.ai_score.toFixed(3);
        manipScore.textContent = result.manipulation_score.toFixed(3);
        
        aiScoreBar.style.width = `${result.ai_score * 100}%`;
        manipScoreBar.style.width = `${result.manipulation_score * 100}%`;
    }
    
    // Update faces
    const facesList = document.getElementById('facesList');
    const facesCount = document.getElementById('facesCount');
    const facesSection = document.getElementById('facesSection');
    
    if (facesCount) {
        facesCount.textContent = result.faces_detected;
    }
    
    if (facesList && facesSection) {
        if (result.faces_detected > 0) {
            facesList.innerHTML = result.faces.map(face => `
                <div class="face-item">
                    Face ${face.face_id + 1}: 
                    ${face.deepfake_score !== null ? 
                        `Deepfake Score: ${face.deepfake_score.toFixed(3)}` : 
                        'No deepfake analysis'}
                </div>
            `).join('');
            facesSection.style.display = 'block';
        } else {
            facesSection.style.display = 'none';
        }
    }
    
    // Update metadata
    const requestId = document.getElementById('requestId');
    if (requestId) {
        requestId.textContent = data.request_id;
    }
    
    // Show upgrade prompt for free users after scan
    if (data.user_type === 'free' && data.scan_info && data.scan_info.scans_left_today <= 0) {
        setTimeout(() => {
            if (confirm('🎯 You\'ve used your free scan!\n\nUpgrade to Premium for unlimited scans, priority processing, and more features!\n\nLearn more about premium?')) {
                window.location.href = '/premium';
            }
        }, 1000);
    }
    
    hideAllSections();
    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) resultsSection.style.display = 'block';
}

function showError(message) {
    const errorText = document.getElementById('errorText');
    if (errorText) {
        errorText.innerHTML = `<p>${message}</p>`;
    }
    
    hideAllSections();
    const errorSection = document.getElementById('errorSection');
    if (errorSection) errorSection.style.display = 'block';
}

function hideAllSections() {
    const sections = [
        'uploadSection', 'previewSection', 'resultsSection', 
        'loadingSection', 'errorSection'
    ];
    
    sections.forEach(section => {
        const element = document.getElementById(section);
        if (element) element.style.display = 'none';
    });
}

function resetAnalysis() {
    currentFile = null;
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    
    hideAllSections();
    const uploadSection = document.getElementById('uploadSection');
    if (uploadSection) uploadSection.style.display = 'block';
    
    // Reload user status to update scan counts
    loadUserStatus();
}

// Drag and drop support
function setupDragAndDrop() {
    const uploadBox = document.getElementById('uploadBox');
    if (!uploadBox) return;

    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#667eea';
        uploadBox.style.background = '#f8f9ff';
    });

    uploadBox.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#ddd';
        uploadBox.style.background = '';
    });

    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#ddd';
        uploadBox.style.background = '';
        
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFileSelect(file);
        }
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    loadUserStatus();
    setupDragAndDrop();
    hideAllSections();
    const uploadSection = document.getElementById('uploadSection');
    if (uploadSection) uploadSection.style.display = 'block';
});
