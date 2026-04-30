(function() {
    if (window.audioControlInitialized) return;
    window.audioControlInitialized = true;

    // Determine the base path for assets
    // If we are in /host/index.html, assets are in ./assets/
    // If we are in /login (which might be served from /host/login.html), we need to be careful.
    // Using relative path 'assets/' usually works if the script is loaded from the same level.
    // But since this script is in assets/, we can use its own location to find the music.
    
    const scriptTag = document.querySelector('script[src*="audio-control.js"]');
    const scriptSrc = scriptTag ? scriptTag.src : '';
    const assetsBase = scriptSrc.substring(0, scriptSrc.lastIndexOf('/') + 1);
    
    const audio = new Audio(assetsBase + 'bg_music.m4a');
    audio.loop = true;
    audio.id = 'bg-audio';

    const btn = document.createElement('button');
    btn.id = 'audio-toggle';
    btn.innerHTML = '🔊'; 
    btn.style.position = 'fixed';
    btn.style.top = '20px';
    btn.style.right = '20px';
    btn.style.zIndex = '10000';
    btn.style.padding = '0';
    btn.style.width = '50px';
    btn.style.height = '50px';
    btn.style.borderRadius = '50%';
    btn.style.border = '3px solid #00d4ff';
    btn.style.backgroundColor = 'rgba(12, 17, 29, 0.9)';
    btn.style.color = '#00d4ff';
    btn.style.cursor = 'pointer';
    btn.style.fontSize = '24px';
    btn.style.display = 'flex';
    btn.style.alignItems = 'center';
    btn.style.justifyContent = 'center';
    btn.style.boxShadow = '0 0 15px rgba(0, 212, 255, 0.5)';
    btn.style.transition = 'all 0.3s ease';
    btn.style.backdropFilter = 'blur(5px)';

    btn.onmouseover = () => {
        btn.style.transform = 'scale(1.1) rotate(10deg)';
        btn.style.boxShadow = '0 0 25px rgba(0, 212, 255, 0.8)';
    };
    btn.onmouseout = () => {
        btn.style.transform = 'scale(1.0) rotate(0deg)';
        btn.style.boxShadow = '0 0 15px rgba(0, 212, 255, 0.5)';
    };

    document.body.appendChild(btn);

    let isMuted = localStorage.getItem('audioMuted') === 'true';
    audio.muted = isMuted;
    btn.innerHTML = isMuted ? '🔇' : '🔊';

    function tryPlay() {
        if (!isMuted) {
            audio.play().catch(e => {
                console.log("Autoplay blocked, waiting for interaction");
                const playOnInteract = () => {
                    if (!isMuted) audio.play();
                    document.removeEventListener('click', playOnInteract);
                    document.removeEventListener('keydown', playOnInteract);
                };
                document.addEventListener('click', playOnInteract);
                document.addEventListener('keydown', playOnInteract);
            });
        }
    }

    if (document.readyState === 'complete') tryPlay();
    else window.addEventListener('load', tryPlay);

    btn.onclick = function(e) {
        e.stopPropagation();
        isMuted = !isMuted;
        audio.muted = isMuted;
        if (!isMuted) {
            audio.play();
            btn.innerHTML = '🔊';
            btn.style.color = '#00d4ff';
            btn.style.borderColor = '#00d4ff';
        } else {
            audio.pause();
            btn.innerHTML = '🔇';
            btn.style.color = '#ff5555';
            btn.style.borderColor = '#ff5555';
        }
        localStorage.setItem('audioMuted', isMuted);
    };
})();
