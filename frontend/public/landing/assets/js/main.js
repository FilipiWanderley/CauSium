!function(){if(!window.UnicornStudio){window.UnicornStudio={isInitialized:!1};var i=document.createElement("script");i.src="https://cdn.jsdelivr.net/gh/hiunicornstudio/unicornstudio.js@v1.4.29/dist/unicornStudio.umd.js",i.onload=function(){window.UnicornStudio.isInitialized||(UnicornStudio.init(),window.UnicornStudio.isInitialized=!0)},(document.head || document.body).appendChild(i)}}();

// Language Definitions
        const translations = {
            "en": {
                // Nav
                "nav_product": "Product",
                "nav_solutions": "Solutions",
                "nav_pricing": "Pricing",
                "nav_signin": "Sign in",
                "nav_demo": "Request Demo",
                
                // Hero
                "hero_badge": "Cloud Cost Decision & Execution Platform",
                "hero_title_1": "Stop Guessing",
                "hero_title_2": "Cloud Costs.",
                "hero_title_3": "Prove What Drives Them — and Act Safely in Production.",
                "hero_desc": "Understand what changed, why it changed, and whether it's safe to act — before touching production. CauSium combines causal attribution, controlled experiments, and risk-aware governance to turn cloud cost insights into safe, validated actions.",
                "hero_btn_demo": "Request Demo",
                "hero_btn_works": "See How It Works",
                "hero_stat1_label": "Validated Cost Reduction",
                "hero_stat2_label": "Time to Safe Execution",
                "hero_stat2_unit": "Min",

                // Not Another Dashboard
                "nad_badge": "Differentiation",
                "nad_title": "Not Another FinOps Dashboard",
                "nad_desc": "CauSium goes beyond visibility with validation, governance, and immutable decision evidence.",
                "nad_item_1": "- Dashboards show data — CauSium explains causality",
                "nad_item_2": "- Recommendations suggest — CauSium validates with experiments",
                "nad_item_3": "- Scripts execute blindly — CauSium enforces risk-aware governance",
                "nad_item_4": "- Logs record events — CauSium produces immutable audit evidence",
                
                // Ticker
                "tick_1": "CAUSAL DECISION ENGINE",
                "tick_2": "CONTROLLED EXPERIMENT EXECUTION",
                "tick_3": "RISK-AWARE GOVERNANCE",
                "tick_4": "IMMUTABLE AUDIT EVIDENCE",
                "tick_5": "MULTI-CLOUD COST CONTROL",
                
                // Features
                "feat1_title": "Causal Attribution",
                "feat1_desc": "Know exactly what changed your cloud costs — with measurable causal confidence across services, workloads, and environments.",
                "feat2_title": "Experiment Engine",
                "feat2_desc": "Validate optimizations in production using controlled experiments, canary rollouts, and automatic rollback when risk thresholds are exceeded.",
                "feat3_title": "Adaptive Prioritization",
                "feat3_desc": "Prioritize cost actions based on real impact, confidence, and risk — not static recommendations or guesswork.",
                "feat4_title": "Risk-Aware Governance",
                "feat4_desc": "Enforce policies, approvals, and risk budgets automatically before any production change is executed.",
                "feat5_title": "Outcome Feedback Loop",
                "feat5_desc": "Continuously improve decisions using real experiment outcomes, validated savings, and post-change performance signals.",
                "feat6_title": "Immutable Audit Trail",
                "feat6_desc": "Every decision and action is recorded with cryptographic evidence, ensuring full auditability and compliance.",
                
                // Proof
                "proof_title1": "From Cost Signal to",
                "proof_title2": "Verified Action",
                "proof_badge": "Optimization Engine",
                "proof_badge_l1": "Guardrails Active",
                "proof_badge_l2": "94% Confidence",
                "proof_h1": "From Cost Signal to",
                "proof_h2": "Safe Execution",
                "proof_h_label": "[LIVE PLATFORM]",
                "proof_h_desc": "Detect anomalies, explain root causes, simulate impact, and execute optimizations safely — all in one decision workflow.",
                "proof_s1_t": "Time to Detection",
                "proof_s1_l1": "Alert",
                "proof_s1_l2": "Actionable",
                "proof_s2_t": "Protected Rollouts",
                "proof_s2_l1": "Risk",
                "proof_s2_l2": "Guarded",
                "proof_s3_t": "Reviewed Opportunities",
                "proof_s3_l1": "Queued",
                "proof_s3_l2": "Ranked",
                "proof_r1": "Built For Safe Optimization",
                "proof_r2": "At Scale",
                "proof_r_desc": "CauSium gives cloud teams a governed path from recommendation to execution across complex multi-cloud environments.",
                "proof_r_stat": "Policy Coverage",
                "proof_c_1": "Savings",
                "proof_c_2": "Velocity",
                "proof_c_desc": "Turning noisy cloud spend into measurable, controlled cost reduction.",
                "proof_c_time": "30 DAYS",
                "proof_c_label": "PROJECTED SAVINGS",
                "proof_m_badge": "[INTEGRATION]",
                "proof_m_1": "Multi-Cloud",
                "proof_m_2": "Deployment Coverage",
                "proof_m_stat": "Supported Environments",
                "proof_m_btn": "Integrate",
                
                // Why
                "why_badge": "Why CauSium",
                "why_h1": "From Visibility to",
                "why_h2": "Controlled Execution",
                "why_desc": "Most tools stop at dashboards. CauSium connects cost visibility to decision-making, controlled execution, and risk-aware governance.",
                "why_btn": "Explore Platform",
                "why1_title": "From Signal to Root Cause",
                "why1_desc": "Surface the highest-impact cost opportunities quickly, without manual spreadsheet work or dashboard hunting.",
                "why2_title": "Simulate Before Acting",
                "why2_desc": "Test changes in controlled environments before rollout, with rollback triggers protecting production health.",
                "why3_title": "Enforced Risk Controls",
                "why3_desc": "Apply policies, approvals, and risk budgets automatically to every critical optimization workflow.",
                "why4_title": "Unified Multi-Cloud Control",
                "why4_desc": "Unify AWS, Azure, and GCP cost intelligence in one operating layer for engineering and FinOps teams.",
                "why5_title": "Verifiable Decision Trail",
                "why5_desc": "Maintain verifiable records of recommendations, decisions, approvals, and execution outcomes.",
                
                // Testimonials
                "test_badge": "Platform Validation",
                "test_h1": "Built for Teams Running",
                "test_h2": "Real Cloud Spend",
                "test1_quote": `"CauSium replaced guesswork with verified decisions. We know what changed, why it changed, and whether it's safe to act."`,
                "test2_quote": `"The experiment workflow changed everything. We can validate optimizations safely before rolling them into production."`,
                "test3_quote": `"What used to take days of cross-checking now takes minutes. We know what changed, why it changed, and whether it is safe to act."`,
                "test4_quote": `"The governance layer is what made adoption possible for us. Policies, approvals, and auditability are built in from day one."`,
                "test5_quote": `"We finally have a platform that connects cost visibility with controlled execution instead of stopping at dashboards."`,
                "test6_quote": `"CauSium gives us a structured way to reduce waste without introducing production risk."`,
                
                // Pricing
                "price_h1": "Pricing Based on Controlled Savings and",
                "price_h2": "Cloud Scale",
                "price_mo": "Monthly",
                "price_yr": "Annual",
                "price_mo_label": "/month",
                "price_best": "Best Value",
                "price_inc": "What's included",
                "p1_desc": "For small teams that need visibility into cloud spend, anomaly detection, and core optimization insights.",
                "p1_f1": "Cloud spend visibility dashboard",
                "p1_f2": "Cost anomaly detection",
                "p1_f3": "Basic opportunity recommendations",
                "p1_f4": "Email alerts",
                "p1_btn": "Start Free Trial",
                "p2_desc": "For growing engineering and FinOps teams that need causal analysis, prioritization, and safer decision workflows.",
                "p2_f1": "Everything in Starter",
                "p2_f2": "Causal attribution engine",
                "p2_f3": "Opportunity prioritization",
                "p2_f4": "Experiment planning workflows",
                "p2_f5": "Slack notifications",
                "p2_btn": "Request Demo",
                "p3_price": "Custom",
                "p3_desc": "For organizations requiring governed execution, advanced approvals, auditability, and multi-cloud operational control.",
                "p3_f1": "Everything in Growth",
                "p3_f2": "Controlled experiments & rollback",
                "p3_f3": "Risk budgets and policy approvals",
                "p3_f4": "Immutable audit trail",
                "p3_f5": "Enterprise support",
                "p3_btn": "Talk to Sales",
                
                // Footer
                "ft_soc1": "Documentation",
                "ft_soc2": "Architecture",
                "ft_soc3": "Security",
                "ft_soc4": "Request Demo",
                "ft_c1_title": "Product",
                "ft_c1_l1": "Platform Overview",
                "ft_c1_l2": "Execution Flow",
                "ft_c1_l3": "Pricing",
                "ft_c1_l4": "Integrations",
                "ft_c2_title": "Platform",
                "ft_c2_l1": "Causal Engine",
                "ft_c2_l2": "Experiment Engine",
                "ft_c2_l3": "Governance",
                "ft_c2_l4": "Audit Trail",
                "ft_c3_title": "Resources",
                "ft_c3_l1": "Documentation",
                "ft_c3_l2": "Architecture",
                "ft_c3_l3": "Security",
                "ft_c3_l4": "API Reference",
                "ft_c4_title": "Company",
                "ft_c4_l1": "About",
                "ft_c4_l2": "Contact",
                "ft_c4_l3": "Privacy",
                "ft_c4_l4": "Terms",
                "ft_status": "MULTI-CLOUD PLATFORM ONLINE"
            },
            "pt": {
                // Nav
                "nav_product": "Produto",
                "nav_solutions": "Soluções",
                "nav_pricing": "Preços",
                "nav_signin": "Entrar",
                "nav_demo": "Solicitar Demo",
                
                // Hero
                "hero_badge": "Plataforma de Inteligência de Custos Cloud",
                "hero_title_1": "Pare de Adivinhar",
                "hero_title_2": "Custos de Cloud.",
                "hero_title_3": "Entenda o que Realmente os Impulsiona.",
                "hero_desc": "O CauSium combina análise causal, experimentos controlados e governança focada em risco para ajudar equipes de FinOps e engenharia a reduzir o desperdício em nuvem com confiança.",
                "hero_btn_demo": "Solicitar Demo",
                "hero_btn_works": "Veja Como Funciona",
                "hero_stat1_label": "Redução de Desperdício",
                "hero_stat2_label": "Tempo para Ação Segura",
                "hero_stat2_unit": "Min",

                // Not Another Dashboard
                "nad_badge": "Diferencial",
                "nad_title": "Não É Apenas Mais Um Dashboard de FinOps",
                "nad_desc": "O CauSium vai além da visibilidade com validação, governança e evidências imutáveis de decisão.",
                "nad_item_1": "- Dashboards mostram dados — o CauSium explica causalidade",
                "nad_item_2": "- Recomendações sugerem — o CauSium valida com experimentos",
                "nad_item_3": "- Scripts executam às cegas — o CauSium aplica governança orientada a risco",
                "nad_item_4": "- Logs registram eventos — o CauSium produz evidências imutáveis de auditoria",
                
                // Ticker
                "tick_1": "ATRIBUIÇÃO CAUSAL",
                "tick_2": "EXPERIMENTOS CONTROLADOS",
                "tick_3": "ORÇAMENTOS DE RISCO",
                "tick_4": "TRILHA DE AUDITORIA IMUTÁVEL",
                "tick_5": "VISIBILIDADE MULTI-CLOUD",
                
                // Features
                "feat1_title": "Atribuição Causal",
                "feat1_desc": "Identifique o que realmente causou as mudanças nos custos da nuvem com pontuações de confiança em cargas de trabalho, serviços e ambientes.",
                "feat2_title": "Motor de Experimentos",
                "feat2_desc": "Teste alterações de otimização com segurança usando implantações controladas, execução canário e reversão automática quando as proteções são rompidas.",
                "feat3_title": "Priorização Adaptativa",
                "feat3_desc": "Classifique as oportunidades de economia de custos por impacto, risco e confiança para que as equipes ajam no que mais importa primeiro.",
                "feat4_title": "Governança Ciente de Riscos",
                "feat4_desc": "Exija aprovações, políticas, janelas de manutenção e orçamentos de risco antes que qualquer ação em produção seja executada.",
                "feat5_title": "Ciclo de Feedback de Resultados",
                "feat5_desc": "Refine as recomendações continuamente usando resultados de experimentos, economia realizada e sinais de desempenho após as mudanças.",
                "feat6_title": "Trilha de Auditoria Imutável",
                "feat6_desc": "Toda ação crítica é registrada com evidências verificáveis, oferecendo às equipes rastreabilidade, conformidade e responsabilidade operacional.",
                
                // Proof
                "proof_title1": "Prova Operacional &",
                "proof_title2": "Impacto da Plataforma",
                "proof_badge": "Motor de Otimização",
                "proof_badge_l1": "Proteções Ativas",
                "proof_badge_l2": "94% de Confiança",
                "proof_h1": "Do Sinal de Custo à",
                "proof_h2": "Execução Segura",
                "proof_h_label": "[PLATAFORMA ONLINE]",
                "proof_h_desc": "DETECTANDO ANOMALIAS DE CUSTOS, EXPLICANDO CAUSAS-RAIZ E EXECUTANDO OTIMIZAÇÕES COM CONTROLES DE SEGURANÇA INTEGRADOS.",
                "proof_s1_t": "Tempo de Detecção",
                "proof_s1_l1": "Alerta",
                "proof_s1_l2": "Acionável",
                "proof_s2_t": "Lançamentos Protegidos",
                "proof_s2_l1": "Risco",
                "proof_s2_l2": "Protegido",
                "proof_s3_t": "Oportunidades Revisadas",
                "proof_s3_l1": "Na Fila",
                "proof_s3_l2": "Classificado",
                "proof_r1": "Criado Para Otimização Segura",
                "proof_r2": "Em Larga Escala",
                "proof_r_desc": "O CauSium fornece às equipes de nuvem um caminho governado, desde a recomendação até a execução em ambientes complexos multi-cloud.",
                "proof_r_stat": "Cobertura de Políticas",
                "proof_c_1": "Velocidade de",
                "proof_c_2": "Economia",
                "proof_c_desc": "Transformando os altos gastos em nuvem em redução de custos mensurável e controlada.",
                "proof_c_time": "30 DIAS",
                "proof_c_label": "ECONOMIA PROJETADA",
                "proof_m_badge": "[INTEGRAÇÃO]",
                "proof_m_1": "Cobertura de",
                "proof_m_2": "Implantação Multi-Cloud",
                "proof_m_stat": "Ambientes Suportados",
                "proof_m_btn": "Integrar",
                
                // Why
                "why_badge": "Por Que o CauSium",
                "why_h1": "Construído Para Clareza,",
                "why_h2": "Controle e Ação Segura",
                "why_desc": "O CauSium ajuda as equipes a sair da simples visibilidade de custos da nuvem para uma ação confiante com explicabilidade, governança e segurança operacional.",
                "why_btn": "Explorar Plataforma",
                "why1_title": "Decisões Mais Rápidas",
                "why1_desc": "Destaque rapidamente as oportunidades de custo de maior impacto, sem o trabalho manual de planilhas ou buscas em vários painéis.",
                "why2_title": "Execução Segura",
                "why2_desc": "Teste alterações em ambientes controlados antes do lançamento, com gatilhos de reversão (rollback) para proteger a integridade da produção.",
                "why3_title": "Governado por Padrão",
                "why3_desc": "Aplique políticas, aprovações e orçamentos de risco automaticamente a cada fluxo de trabalho crítico de otimização.",
                "why4_title": "Criado para Multi-Cloud",
                "why4_desc": "Unifique a inteligência de custos da AWS, Azure e GCP em uma única camada operacional para as equipes de engenharia e FinOps.",
                "why5_title": "Pronto para Auditoria",
                "why5_desc": "Mantenha registros facilmente verificáveis de todas as recomendações, decisões, aprovações e resultados de execução.",
                
                // Testimonials
                "test_badge": "Validação da Plataforma",
                "test_h1": "Construído para Equipes Com",
                "test_h2": "Gastos Reais em Cloud",
                "test1_quote": `"O CauSium nos ajudou a separar o ruído dos verdadeiros geradores de custos. Nossa equipe parou de reagir às cegas e começou a priorizar com confiança."`,
                "test2_quote": `"O fluxo de trabalho de experimentos mudou tudo. Podemos validar as otimizações com total segurança antes de implantá-las na produção."`,
                "test3_quote": `"O que antes levava dias de verificação agora leva minutos. Sabemos o que mudou, por que mudou e se é seguro agir."`,
                "test4_quote": `"A camada de governança foi o que tornou nossa adoção possível. Políticas, aprovações e capacidade de auditoria estão integradas desde o primeiro dia."`,
                "test5_quote": `"Finalmente temos uma plataforma que conecta a visibilidade de custos à execução controlada, em vez de parar apenas nos relatórios e gráficos."`,
                "test6_quote": `"O CauSium nos fornece uma forma bem estruturada de reduzir o desperdício sem introduzir nenhum risco extra na nossa produção."`,
                
                // Pricing
                "price_h1": "Preços que Escalam com",
                "price_h2": "A Sua Pegada Na Nuvem",
                "price_mo": "Mensal",
                "price_yr": "Anual",
                "price_mo_label": "/mês",
                "price_best": "Mais Popular",
                "price_inc": "O que está incluído",
                "p1_desc": "Para pequenas equipes que precisam de visibilidade dos gastos na nuvem, detecção de anomalias e as principais dicas de otimização.",
                "p1_f1": "Painel de visibilidade de custos",
                "p1_f2": "Detecção de anomalias de custos",
                "p1_f3": "Recomendações básicas de oportunidades",
                "p1_f4": "Alertas por e-mail",
                "p1_btn": "Iniciar Teste Grátis",
                "p2_desc": "Para equipes de engenharia e FinOps em crescimento que precisam de análise causal, priorização e fluxos de decisão mais seguros.",
                "p2_f1": "Tudo do plano Starter",
                "p2_f2": "Motor de atribuição causal",
                "p2_f3": "Priorização de oportunidades",
                "p2_f4": "Fluxos de planejamento de experimentos",
                "p2_f5": "Notificações no Slack",
                "p2_btn": "Solicitar Demonstração",
                "p3_price": "Sob Consulta",
                "p3_desc": "Para organizações que exigem execução governada, aprovações avançadas, auditabilidade e total controle operacional multi-cloud.",
                "p3_f1": "Tudo do plano Growth",
                "p3_f2": "Experimentos controlados e rollback",
                "p3_f3": "Orçamentos de risco e aprovação de políticas",
                "p3_f4": "Trilha de auditoria imutável",
                "p3_f5": "Suporte corporativo prioritário",
                "p3_btn": "Falar com Vendas",
                
                // Footer
                "ft_soc1": "Documentação",
                "ft_soc2": "Arquitetura",
                "ft_soc3": "Segurança",
                "ft_soc4": "Solicitar Demo",
                "ft_c1_title": "Produto",
                "ft_c1_l1": "Platform Overview",
                "ft_c1_l2": "Execution Flow",
                "ft_c1_l3": "Preços",
                "ft_c1_l4": "Integrações",
                "ft_c2_title": "Plataforma",
                "ft_c2_l1": "Motor Causal",
                "ft_c2_l2": "Motor de Experimentos",
                "ft_c2_l3": "Governança",
                "ft_c2_l4": "Trilha de Auditoria",
                "ft_c3_title": "Recursos",
                "ft_c3_l1": "Documentação",
                "ft_c3_l2": "Arquitetura",
                "ft_c3_l3": "Segurança",
                "ft_c3_l4": "Referência da API",
                "ft_c4_title": "Empresa",
                "ft_c4_l1": "Sobre",
                "ft_c4_l2": "Contato",
                "ft_c4_l3": "Privacidade",
                "ft_c4_l4": "Termos",
                "ft_status": "PLATAFORMA MULTI-CLOUD ONLINE"
            }
        };

        // Language Handling Logic
        // Read from React app key first, fallback to landing key, then default 'en'
        let currentLang = localStorage.getItem('causium:lang') || localStorage.getItem('causium_lang') || 'en';

        function setLanguage(lang) {
            currentLang = lang;
            localStorage.setItem('causium_lang', lang);
            localStorage.setItem('causium:lang', lang); // sync with React app
            document.documentElement.lang = lang === 'pt' ? 'pt-BR' : 'en';
            document.getElementById('currentLangText').innerText = lang.toUpperCase();

            // Update all translated elements
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[lang] && translations[lang][key]) {
                    el.innerText = translations[lang][key];
                }
            });
        }

        document.addEventListener("DOMContentLoaded", () => {
            // Apply saved language on load
            setLanguage(currentLang);

            // Smooth scroll for all hash links
            document.querySelectorAll('a[href^="#"]').forEach(link => {
                link.addEventListener("click", (event) => {
                    const targetId = link.getAttribute("href").substring(1);
                    if (!targetId) {
                        event.preventDefault();
                        return;
                    }
                    const targetEl = document.getElementById(targetId);
                    if (targetEl) {
                        event.preventDefault();
                        targetEl.scrollIntoView({ behavior: "smooth", block: "start" });
                        history.replaceState(null, "", `#${targetId}`);
                    }
                });
            });

            // Mobile Menu Toggle Logic
            const mobileMenuBtn = document.getElementById('mobileMenuBtn');
            const mobileMenu = document.getElementById('mobileMenu');
            if (mobileMenuBtn && mobileMenu) {
                mobileMenuBtn.addEventListener('click', () => {
                    mobileMenu.classList.toggle('hidden');
                });
                
                // Close menu when clicking a link
                document.querySelectorAll('.mobile-link').forEach(link => {
                    link.addEventListener('click', () => {
                        mobileMenu.classList.add('hidden');
                    });
                });
            }

            // Setup language toggle button
            const langToggleBtn = document.getElementById('langToggle');
            if (langToggleBtn) {
                langToggleBtn.addEventListener('click', () => {
                    setLanguage(currentLang === 'en' ? 'pt' : 'en');
                });
            }

            // Initialize Lucide Icons
            lucide.createIcons();

            // Intersection Observer for Scroll Animations
            const observer = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("animate");
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1, rootMargin: "0px 0px -5% 0px" });

            document.querySelectorAll(".animate-on-scroll").forEach((el) => {
                observer.observe(el);
            });

            // Spotlight Card Hover Effect
            const cards = document.querySelectorAll(".spotlight-card");
            document.addEventListener("mousemove", (e) => {
                cards.forEach(card => {
                    const rect = card.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    card.style.setProperty("--mouse-x", `${x}px`);
                    card.style.setProperty("--mouse-y", `${y}px`);
                });
            });
        });

