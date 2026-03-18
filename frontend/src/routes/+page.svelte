<script lang="ts">
	import { onDestroy } from 'svelte';

	let videoEl: HTMLVideoElement;
	let canvasEl: HTMLCanvasElement;
	let stream: MediaStream | null = $state(null);
	let isStreaming = $state(false);
	let prediction = $state('—');
	let confidence = $state(0);
	let statusText = $state('Camera off');
	let isLoading = $state(false);
	let errorMsg = $state('');
	let intervalId: ReturnType<typeof setInterval> | null = null;
	let requestInFlight = false;
	let history: { letter: string; confidence: number; time: number }[] = $state([]);

	async function startCamera() {
		try {
			errorMsg = '';
			statusText = 'Requesting camera access…';
			stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: 'user', width: 640, height: 480 }
			});
			videoEl.srcObject = stream;
			await videoEl.play();
			isStreaming = true;
			statusText = 'Streaming';
			startPredictionLoop();
		} catch (err) {
			errorMsg = `Camera access denied: ${err}`;
			statusText = 'Error';
		}
	}

	function stopCamera() {
		if (intervalId) {
			clearInterval(intervalId);
			intervalId = null;
		}
		if (stream) {
			stream.getTracks().forEach((t) => t.stop());
			stream = null;
		}
		isStreaming = false;
		requestInFlight = false;
		statusText = 'Camera off';
		prediction = '—';
		confidence = 0;
	}

	function startPredictionLoop() {
		intervalId = setInterval(captureAndPredict, 500);
	}

	async function captureAndPredict() {
		if (!videoEl || !canvasEl || !isStreaming || requestInFlight) return;

		const ctx = canvasEl.getContext('2d')!;
		canvasEl.width = videoEl.videoWidth;
		canvasEl.height = videoEl.videoHeight;
		ctx.drawImage(videoEl, 0, 0);

		const base64 = canvasEl.toDataURL('image/jpeg', 0.8);

		try {
			requestInFlight = true;
			isLoading = true;
			const res = await fetch('/api/predict', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ image: base64 })
			});

			if (!res.ok) throw new Error(`Server error: ${res.status}`);

			const data = await res.json();
			prediction = data.prediction;
			confidence = data.confidence;
			errorMsg = '';

			// Add to history (keep last 10)
			if (data.prediction !== 'nothing') {
				history = [
					{ letter: data.prediction, confidence: data.confidence, time: Date.now() },
					...history
				].slice(0, 10);
			}
		} catch (err) {
			errorMsg = `Prediction failed: ${err}`;
		} finally {
			requestInFlight = false;
			isLoading = false;
		}
	}

	function clearHistory() {
		history = [];
	}

	onDestroy(() => {
		stopCamera();
	});
</script>

<svelte:head>
	<title>ASL Sign Language Recognition</title>
	<meta name="description" content="Real-time ASL sign language recognition using AI" />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<main class="app-container">
	<!-- Ambient glow effects -->
	<div class="ambient-glow glow-1"></div>
	<div class="ambient-glow glow-2"></div>
	<div class="ambient-glow glow-3"></div>

	<header class="app-header">
		<div class="logo">
			<h1>SignLens</h1>
		</div>
	</header>

	<div class="main-grid">
		<!-- Webcam Panel -->
		<section class="panel webcam-panel" id="webcam-panel">
			<div class="panel-header">
				<h2>📸 Camera Feed</h2>
				<div class="status-badge" class:active={isStreaming} class:error={!!errorMsg}>
					<span class="status-dot"></span>
					{statusText}
				</div>
			</div>

			<div class="video-wrapper" id="video-wrapper">
				<video bind:this={videoEl} playsinline muted class="video-feed" class:hidden={!isStreaming}>
					<track kind="captions" />
				</video>

				{#if !isStreaming}
					<div class="video-placeholder">
						<span class="placeholder-icon">📷</span>
						<p>Start the camera to begin recognition</p>
					</div>
				{/if}

				{#if isStreaming && prediction !== '—'}
					<div class="prediction-overlay" class:high-confidence={confidence > 0.8}>
						<span class="overlay-letter">{prediction}</span>
						<span class="overlay-confidence">{(confidence * 100).toFixed(1)}%</span>
					</div>
				{/if}

				{#if isLoading}
					<div class="loading-indicator">
						<div class="spinner"></div>
					</div>
				{/if}
			</div>

			<canvas bind:this={canvasEl} class="hidden-canvas"></canvas>

			<div class="controls">
				{#if !isStreaming}
					<button class="btn btn-primary" onclick={startCamera} id="start-camera-btn">
						<span>▶</span> Start Camera
					</button>
				{:else}
					<button class="btn btn-danger" onclick={stopCamera} id="stop-camera-btn">
						<span>■</span> Stop Camera
					</button>
				{/if}
			</div>

			{#if errorMsg}
				<div class="error-banner" id="error-banner">
					{errorMsg}
				</div>
			{/if}
		</section>

		<!-- Results Panel -->
		<section class="panel results-panel" id="results-panel">
			<div class="panel-header">
				<h2>🔤 Recognition</h2>
			</div>

			<!-- Current Prediction -->
			<div class="current-prediction" id="current-prediction">
				<div class="prediction-card" class:active={isStreaming && prediction !== '—'}>
					<span class="big-letter" class:pulse={isLoading}>{prediction}</span>
					<div class="confidence-bar-wrapper">
						<div class="confidence-bar" style="width: {confidence * 100}%"></div>
					</div>
					<span class="confidence-text"
						>{confidence > 0 ? `${(confidence * 100).toFixed(1)}% confidence` : 'Waiting…'}</span
					>
				</div>
			</div>

			<!-- History -->
			<div class="history-section">
				<div class="history-header">
					<h3>History</h3>
					{#if history.length > 0}
						<button class="btn-ghost" onclick={clearHistory}>Clear</button>
					{/if}
				</div>
				<div class="history-list" id="history-list">
					{#if history.length === 0}
						<p class="history-empty">No predictions yet</p>
					{:else}
						{#each history as item, i}
							<div
								class="history-item"
								style="animation-delay: {i * 50}ms"
							>
								<span class="history-letter">{item.letter}</span>
								<span class="history-conf">{(item.confidence * 100).toFixed(0)}%</span>
							</div>
						{/each}
					{/if}
				</div>
			</div>
		</section>
	</div>
</main>

<style>
	/* ═══════════════════════════════════════════
	   DESIGN SYSTEM
	   ═══════════════════════════════════════════ */
	:root {
		--font: 'Inter', system-ui, -apple-system, sans-serif;

		/* Colors */
		--bg-primary: #0a0a0f;
		--bg-secondary: #12121a;
		--bg-card: rgba(255, 255, 255, 0.03);
		--bg-card-hover: rgba(255, 255, 255, 0.06);

		--border: rgba(255, 255, 255, 0.08);
		--border-active: rgba(99, 102, 241, 0.5);

		--text-primary: #f0f0f5;
		--text-secondary: #8b8b9e;
		--text-muted: #55556a;

		--accent: #6366f1;
		--accent-light: #818cf8;
		--accent-glow: rgba(99, 102, 241, 0.25);

		--success: #22c55e;
		--danger: #ef4444;
		--warning: #f59e0b;

		/* Spacing */
		--radius: 16px;
		--radius-sm: 10px;
		--radius-xs: 6px;
	}

	/* ═══════════════════════════════════════════
	   LAYOUT
	   ═══════════════════════════════════════════ */
	.app-container {
		font-family: var(--font);
		min-height: 100vh;
		background: var(--bg-primary);
		color: var(--text-primary);
		padding: 2rem;
		position: relative;
		overflow: hidden;
	}

	/* Ambient glow effects */
	.ambient-glow {
		position: fixed;
		border-radius: 50%;
		filter: blur(120px);
		pointer-events: none;
		z-index: 0;
	}
	.glow-1 {
		width: 600px;
		height: 600px;
		background: rgba(99, 102, 241, 0.08);
		top: -200px;
		left: -100px;
		animation: float 20s ease-in-out infinite;
	}
	.glow-2 {
		width: 500px;
		height: 500px;
		background: rgba(139, 92, 246, 0.06);
		bottom: -150px;
		right: -100px;
		animation: float 25s ease-in-out infinite reverse;
	}
	.glow-3 {
		width: 400px;
		height: 400px;
		background: rgba(34, 197, 94, 0.04);
		top: 50%;
		left: 50%;
		animation: float 30s ease-in-out infinite;
	}

	@keyframes float {
		0%,
		100% {
			transform: translate(0, 0);
		}
		33% {
			transform: translate(30px, -30px);
		}
		66% {
			transform: translate(-20px, 20px);
		}
	}

	/* ═══════════════════════════════════════════
	   HEADER
	   ═══════════════════════════════════════════ */
	.app-header {
		text-align: center;
		margin-bottom: 2.5rem;
		position: relative;
		z-index: 1;
	}

	.logo {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		margin-bottom: 0.5rem;
	}

	.logo h1 {
		font-size: 2.5rem;
		font-weight: 800;
		background: linear-gradient(135deg, var(--accent-light), #a78bfa, #c084fc);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		letter-spacing: -0.02em;
	}


	/* ═══════════════════════════════════════════
	   GRID
	   ═══════════════════════════════════════════ */
	.main-grid {
		display: grid;
		grid-template-columns: 1.4fr 1fr;
		gap: 1.5rem;
		max-width: 1200px;
		margin: 0 auto;
		position: relative;
		z-index: 1;
	}

	@media (max-width: 900px) {
		.main-grid {
			grid-template-columns: 1fr;
		}
	}

	/* ═══════════════════════════════════════════
	   PANELS (Glassmorphism)
	   ═══════════════════════════════════════════ */
	.panel {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1.5rem;
		backdrop-filter: blur(20px);
		-webkit-backdrop-filter: blur(20px);
		transition: border-color 0.3s ease;
	}

	.panel:hover {
		border-color: rgba(255, 255, 255, 0.12);
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.25rem;
	}

	.panel-header h2 {
		font-size: 1.1rem;
		font-weight: 600;
		color: var(--text-primary);
	}

	/* ═══════════════════════════════════════════
	   STATUS BADGE
	   ═══════════════════════════════════════════ */
	.status-badge {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 0.85rem;
		border-radius: 100px;
		font-size: 0.8rem;
		font-weight: 500;
		background: rgba(255, 255, 255, 0.05);
		color: var(--text-secondary);
		border: 1px solid var(--border);
	}

	.status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--text-muted);
		transition: background 0.3s ease;
	}

	.status-badge.active .status-dot {
		background: var(--success);
		box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
		animation: pulse-dot 2s ease-in-out infinite;
	}

	.status-badge.error .status-dot {
		background: var(--danger);
		box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
	}

	@keyframes pulse-dot {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	/* ═══════════════════════════════════════════
	   VIDEO / WEBCAM
	   ═══════════════════════════════════════════ */
	.video-wrapper {
		position: relative;
		border-radius: var(--radius-sm);
		overflow: hidden;
		background: var(--bg-secondary);
		aspect-ratio: 4 / 3;
		border: 1px solid var(--border);
	}

	.video-feed {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
		transform: scaleX(-1);
	}

	.video-feed.hidden {
		display: none;
	}

	.video-placeholder {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		color: var(--text-muted);
		gap: 0.75rem;
	}

	.placeholder-icon {
		font-size: 3rem;
		opacity: 0.5;
	}

	.video-placeholder p {
		font-size: 0.9rem;
	}

	/* Prediction overlay on video */
	.prediction-overlay {
		position: absolute;
		top: 1rem;
		right: 1rem;
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(12px);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		padding: 0.75rem 1rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
		animation: fadeIn 0.3s ease;
	}

	.prediction-overlay.high-confidence {
		border-color: var(--accent);
		box-shadow: 0 0 20px var(--accent-glow);
	}

	.overlay-letter {
		font-size: 2rem;
		font-weight: 800;
		background: linear-gradient(135deg, var(--accent-light), #a78bfa);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.overlay-confidence {
		font-size: 0.75rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Loading spinner */
	.loading-indicator {
		position: absolute;
		bottom: 1rem;
		left: 1rem;
	}

	.spinner {
		width: 20px;
		height: 20px;
		border: 2px solid rgba(255, 255, 255, 0.1);
		border-top-color: var(--accent-light);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.hidden-canvas {
		display: none;
	}

	/* ═══════════════════════════════════════════
	   CONTROLS
	   ═══════════════════════════════════════════ */
	.controls {
		margin-top: 1.25rem;
		display: flex;
		gap: 0.75rem;
	}

	.btn {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.7rem 1.5rem;
		border-radius: var(--radius-xs);
		font-size: 0.9rem;
		font-weight: 600;
		font-family: var(--font);
		cursor: pointer;
		border: none;
		transition: all 0.2s ease;
		flex: 1;
		justify-content: center;
	}

	.btn-primary {
		background: linear-gradient(135deg, var(--accent), #7c3aed);
		color: white;
		box-shadow: 0 4px 15px var(--accent-glow);
	}

	.btn-primary:hover {
		transform: translateY(-1px);
		box-shadow: 0 6px 25px var(--accent-glow);
	}

	.btn-primary:active {
		transform: translateY(0);
	}

	.btn-danger {
		background: rgba(239, 68, 68, 0.15);
		color: var(--danger);
		border: 1px solid rgba(239, 68, 68, 0.3);
	}

	.btn-danger:hover {
		background: rgba(239, 68, 68, 0.25);
	}

	/* ═══════════════════════════════════════════
	   ERROR BANNER
	   ═══════════════════════════════════════════ */
	.error-banner {
		margin-top: 1rem;
		padding: 0.75rem 1rem;
		border-radius: var(--radius-xs);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid rgba(239, 68, 68, 0.2);
		color: #fca5a5;
		font-size: 0.85rem;
	}

	/* ═══════════════════════════════════════════
	   RESULTS PANEL
	   ═══════════════════════════════════════════ */
	.current-prediction {
		margin-bottom: 1.5rem;
	}

	.prediction-card {
		text-align: center;
		padding: 2rem 1rem;
		background: var(--bg-secondary);
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		transition: all 0.3s ease;
	}

	.prediction-card.active {
		border-color: var(--border-active);
		box-shadow: 0 0 30px var(--accent-glow), inset 0 0 30px rgba(99, 102, 241, 0.03);
	}

	.big-letter {
		display: block;
		font-size: 5rem;
		font-weight: 900;
		line-height: 1;
		margin-bottom: 1rem;
		background: linear-gradient(135deg, var(--accent-light), #a78bfa, #c084fc);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		transition: transform 0.2s ease;
	}

	.big-letter.pulse {
		animation: letter-pulse 0.5s ease;
	}

	@keyframes letter-pulse {
		50% {
			transform: scale(1.05);
		}
	}

	.confidence-bar-wrapper {
		width: 100%;
		height: 4px;
		background: rgba(255, 255, 255, 0.06);
		border-radius: 100px;
		overflow: hidden;
		margin-bottom: 0.75rem;
	}

	.confidence-bar {
		height: 100%;
		background: linear-gradient(90deg, var(--accent), var(--accent-light));
		border-radius: 100px;
		transition: width 0.3s ease;
	}

	.confidence-text {
		font-size: 0.85rem;
		color: var(--text-secondary);
		font-weight: 500;
	}

	/* ═══════════════════════════════════════════
	   HISTORY
	   ═══════════════════════════════════════════ */
	.history-section {
		margin-bottom: 1.5rem;
	}

	.history-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.75rem;
	}

	.history-header h3 {
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text-secondary);
	}

	.btn-ghost {
		background: none;
		border: none;
		color: var(--text-muted);
		font-size: 0.8rem;
		font-family: var(--font);
		cursor: pointer;
		padding: 0.25rem 0.5rem;
		border-radius: var(--radius-xs);
		transition: color 0.2s ease;
	}

	.btn-ghost:hover {
		color: var(--text-secondary);
	}

	.history-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.history-empty {
		color: var(--text-muted);
		font-size: 0.85rem;
	}

	.history-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
		padding: 0.5rem 0.65rem;
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border);
		border-radius: var(--radius-xs);
		animation: slideIn 0.3s ease forwards;
		opacity: 0;
	}

	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(8px) scale(0.95);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.history-letter {
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--accent-light);
	}

	.history-conf {
		font-size: 0.65rem;
		color: var(--text-muted);
		font-weight: 500;
	}

</style>
