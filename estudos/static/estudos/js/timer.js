class StudyTimer {
    constructor(sessaoId, csrfToken) {
        this.sessaoId = sessaoId;
        this.csrfToken = csrfToken;
        this.timerInterval = null;
        this.tempoRestante = 0;
        this.duracaoTotalEtapa = 0;
        this.estado = '';
        this.audioContext = null;

        this.initElements();
        this.sincronizar();
        this.iniciarLoop();
    }

    initElements() {
        this.display = document.getElementById('timer-display');
        this.badgeEtapa = document.getElementById('badge-etapa');
        this.progressBar = document.getElementById('progress-bar');
        this.ciclosText = document.getElementById('ciclos-text');
        this.btnPausar = document.getElementById('btn-pausar');
        this.btnRetomar = document.getElementById('btn-retomar');
    }

    async sincronizar() {
        try {
            const res = await fetch(`/api/timer/${this.sessaoId}/estado/`);
            const data = await res.json();

            if (data.estado === 'CONCLUIDO' || data.estado === 'CANCELADO') {
                window.location.href = '/';
                return;
            }

            this.tempoRestante = data.tempo_restante_segundos;
            this.estado = data.estado;
            this.atualizarInterface(data);
        } catch (err) {
            console.error("Erro ao sincronizar com servidor:", err);
        }
    }

    iniciarLoop() {
        this.timerInterval = setInterval(() => {
            if (this.estado === 'EM_ANDAMENTO' || this.estado === 'EM_DESCANSO') {
                if (this.tempoRestante > 0) {
                    this.tempoRestante--;
                    this.renderTime();
                } else {
                    this.tocarAlarme();
                    this.sincronizar();
                }
            }
        }, 1000);

        // Sincronização periódica a cada 15 segundos para evitar drifts de aba em background
        setInterval(() => this.sincronizar(), 15000);
    }

    renderTime() {
        const m = Math.floor(this.tempoRestante / 60).toString().padStart(2, '0');
        const s = (this.tempoRestante % 60).toString().padStart(2, '0');
        this.display.textContent = `${m}:${s}`;
        document.title = `(${m}:${s}) Sessão de Estudo`;

        if (this.duracaoTotalEtapa > 0) {
            const pct = ((this.duracaoTotalEtapa - this.tempoRestante) / this.duracaoTotalEtapa) * 100;
            this.progressBar.style.width = `${Math.min(100, Math.max(0, pct))}%`;
        }
    }

    atualizarInterface(data) {
        this.badgeEtapa.textContent = data.etapa_atual;
        this.badgeEtapa.className = 'badge-etapa ' + 
            (data.estado === 'PAUSADO' ? 'etapa-pausado' : 
            (data.etapa_code === 'FOCO' ? 'etapa-foco' : 'etapa-descanso'));

        this.ciclosText.textContent = `Ciclo ${data.ciclos_concluidos} de ${data.total_ciclos}`;
        
        if (this.duracaoTotalEtapa === 0 || this.estado !== data.estado) {
            this.duracaoTotalEtapa = data.tempo_restante_segundos;
        }

        if (data.estado === 'PAUSADO') {
            this.btnPausar.classList.add('d-none');
            this.btnRetomar.classList.remove('d-none');
        } else {
            this.btnPausar.classList.remove('d-none');
            this.btnRetomar.classList.add('d-none');
        }

        this.renderTime();
    }

    async acao(endpoint) {
        await fetch(`/api/timer/${this.sessaoId}/${endpoint}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.csrfToken,
                'Content-Type': 'application/json'
            }
        });
        this.sincronizar();
    }

    tocarAlarme() {
        try {
            if (!this.audioContext) this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const osc = this.audioContext.createOscillator();
            const gain = this.audioContext.createGain();
            osc.connect(gain);
            gain.connect(this.audioContext.destination);
            osc.frequency.value = 880; // A5
            gain.gain.setValueAtTime(0.1, this.audioContext.currentTime);
            osc.start();
            osc.stop(this.audioContext.currentTime + 0.5);
        } catch (e) {
            console.log("Notificação de áudio bloqueada pelo navegador.");
        }
    }
}