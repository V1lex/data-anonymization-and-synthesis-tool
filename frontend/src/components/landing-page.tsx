"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { DotGridBackground } from "@/components/dot-grid-background";
import { Reveal } from "@/components/reveal";
import { useLanguage } from "@/components/language-provider";

const GENERATE_PHASE_STEPS = [
  { phase: "launch", at: 1400 },
  { phase: "files", at: 2550 },
] as const;

const ANONYMIZE_PHASE_STEPS = [
  { phase: "masking", at: 1400 },
  { phase: "done", at: 2550 },
] as const;

const SIMILAR_PHASE_STEPS = [
  { phase: "split", at: 1400 },
  { phase: "done", at: 3000 },
] as const;

const content = {
  ru: {
    heroEyebrow: "Data workflows for you",
    heroTitle: "Synthetic Data Generator & Anonymizer",
    heroDescription:
      "Генерируйте учебные и тестовые CSV, анонимизируйте чувствительные поля и создавайте похожие датасеты в одном инструменте.",
    heroPrimary: "Начать",
    heroSecondary: "Как это работает",
    sections: [
      {
        href: "/generate",
        tag: "Generate",
        title: "Создавайте синтетические таблицы с правильными связями и логикой.",
        description:
          "Users, orders, payments, products и support tickets генерируются как согласованный набор данных с реалистичными правилами по датам, валютам, статусам и городам.",
        action: "Перейти к Generate",
      },
      {
        href: "/anonymize",
        tag: "Anonymize",
        title: "Загружайте CSV и сразу получайте рекомендуемые правила по колонкам.",
        description:
          "Детектор определяет типы полей, система предлагает метод, а вы можете вручную скорректировать каждую колонку перед скачиванием результата.",
        action: "Перейти к Anonymize",
      },
      {
        href: "/similar",
        tag: "Similar",
        title: "Создавайте похожий синтетический датасет из произвольного CSV.",
        description:
          "Сервис анализирует структуру, обучает модель, а затем создаёт выборку и применяет постобработку, чтобы результат выглядел правдоподобно.",
        action: "Перейти к Similar",
      },
    ],
    howItWorksTitle: "Как это работает?",
    howItWorksSteps: [
      {
        title: "Выбираете сценарий",
        description: "Generate для шаблонов, Anonymize для защищённой выгрузки, Similar для синтетики по реальному примеру.",
      },
      {
        title: "Настраиваете поток",
        description: "Количество строк, локаль, правила по колонкам, размер результата и предпросмотр данных на каждом шаге.",
      },
      {
        title: "Скачиваете результат",
        description: "Получаете CSV или ZIP, готовый для демо, разработки, тестов и учебных ML-проектов.",
      },
    ],
    datasetsTitle: "Для чего можно применять",
    datasetsDescription:
      "Выберите сценарий в Generate, и товары/услуги в синтетическом каталоге будут соответствовать выбранной предметной области.",
    datasets: ["Электронная коммерция", "Финтех", "Продуктовые магазины", "Логистика", "Образование", "CRM"],
  },
  en: {
    heroEyebrow: "Data workflows for you",
    heroTitle: "Synthetic Data Generator & Anonymizer",
    heroDescription:
      "Generate training and testing CSVs, anonymize sensitive columns, and build similar datasets in one product surface.",
    heroPrimary: "Get started",
    heroSecondary: "How it works",
    sections: [
      {
        href: "/generate",
        tag: "Generate",
        title: "Build synthetic tables with consistent relations and semantics.",
        description:
          "Users, orders, payments, products, and support tickets are generated as a coherent dataset with realistic rules for dates, currencies, statuses, and cities.",
        action: "Start Generate",
      },
      {
        href: "/anonymize",
        tag: "Anonymize",
        title: "Upload a CSV and instantly get suggested rules for each column.",
        description:
          "The detector identifies field types, the suggester recommends a method, and you can still adjust every column before downloading the result.",
        action: "Start Anonymize",
      },
      {
        href: "/similar",
        tag: "Similar",
        title: "Create a similar synthetic dataset from any single-table CSV.",
        description:
          "The backend analyzes structure, fits an SDV model, then samples and post-processes rows so the result stays believable.",
        action: "Start Similar",
      },
    ],
    howItWorksTitle: "How does it work?",
    howItWorksSteps: [
      {
        title: "Choose a workflow",
        description: "Generate for templates, Anonymize for protected exports, Similar for synthetic data from a real-looking example.",
      },
      {
        title: "Tune the flow",
        description: "Set row count, locale, per-column rules, result size, and inspect previews before the final run.",
      },
      {
        title: "Download the result",
        description: "Get a CSV or ZIP ready for demos, development, testing, and academic ML projects.",
      },
    ],
    datasetsTitle: "Where you can apply it",
    datasetsDescription:
      "Choose a Generate use case, and product or service names in the synthetic catalog will match that domain.",
    datasets: ["E-commerce", "Fintech", "Grocery stores", "Logistics", "EdTech", "CRM"],
  },
} as const;

function useViewportPhaseSequence<T extends string>({
  initialPhase,
  steps,
  threshold = 0.18,
  rootMargin = "0px 0px -10% 0px",
}: {
  initialPhase: T;
  steps: ReadonlyArray<{ at: number; phase: T }>;
  threshold?: number;
  rootMargin?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const isVisibleRef = useRef(false);
  const timersRef = useRef<number[]>([]);
  const [phase, setPhase] = useState<T | "idle">("idle");

  useEffect(() => {
    const node = containerRef.current;

    if (!node) {
      return;
    }

    const clearTimers = () => {
      for (const timerId of timersRef.current) {
        window.clearTimeout(timerId);
      }
      timersRef.current = [];
    };

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry) {
          return;
        }

        if (entry.isIntersecting && !isVisibleRef.current) {
          isVisibleRef.current = true;
          clearTimers();
          setPhase(initialPhase);
          timersRef.current = steps.map((step) =>
            window.setTimeout(() => {
              setPhase(step.phase);
            }, step.at),
          );
          return;
        }

        if (!entry.isIntersecting && isVisibleRef.current) {
          isVisibleRef.current = false;
          clearTimers();
          setPhase("idle");
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(node);
    return () => {
      observer.disconnect();
      clearTimers();
    };
  }, [initialPhase, rootMargin, steps, threshold]);

  return { containerRef, phase };
}

function SceneDocument({
  accent,
  className = "",
}: {
  accent: "blue" | "green" | "red";
  className?: string;
}) {
  return (
    <g className={`scene-document scene-document--${accent}${className ? ` ${className}` : ""}`}>
      <path
        className="scene-document__sheet"
        d="M-38 -50H16L40 -26V54c0 7-5 12-12 12h-54c-7 0-12-5-12-12V-38c0-7 5-12 12-12Z"
      />
      <path className="scene-document__fold-fill" d="M16 -50v20c0 2 1 4 3 4h21Z" />
      <path className="scene-document__fold-stroke" d="M16 -50v20c0 2 1 4 3 4h21" />
      <rect className="scene-document__line scene-document__line--one" x="-18" y="-20" width="38" height="7" rx="3.5" />
      <rect className="scene-document__line scene-document__line--two" x="-18" y="-4" width="46" height="7" rx="3.5" />
      <rect className="scene-document__line scene-document__line--three" x="-18" y="12" width="30" height="7" rx="3.5" />
      <text className="scene-document__label" x="1" y="38" textAnchor="middle">
        CSV
      </text>
    </g>
  );
}

function DatasetIllustration({ index }: { index: number }) {
  switch (index) {
    case 0:
      return (
        <svg className="dataset-card__svg" viewBox="0 0 160 120" aria-hidden="true">
          <path className="dataset-svg__panel" d="M42 34h76a14 14 0 0 1 14 14v42a14 14 0 0 1-14 14H42a14 14 0 0 1-14-14V48a14 14 0 0 1 14-14Z" />
          <path className="dataset-svg__outline" d="M54 34v-6c0-8 6-14 14-14h24c8 0 14 6 14 14v6" />
          <path className="dataset-svg__accent" d="M50 58h60M50 72h44M50 86h54" />
        </svg>
      );
    case 1:
      return (
        <svg className="dataset-card__svg" viewBox="0 0 160 120" aria-hidden="true">
          <circle className="dataset-svg__coin" cx="80" cy="60" r="28" />
          <text className="dataset-svg__symbol" x="80" y="70" textAnchor="middle">
            $
          </text>
        </svg>
      );
    case 2:
      return (
        <svg className="dataset-card__svg" viewBox="0 0 160 120" aria-hidden="true">
          <circle className="dataset-svg__panel" cx="80" cy="44" r="18" />
          <path className="dataset-svg__panel" d="M46 96c3-21 17-34 34-34s31 13 34 34Z" />
          <path className="dataset-svg__outline" d="M58 44a22 22 0 0 1 44 0" />
          <path className="dataset-svg__outline" d="M58 46c-10 0-18 8-18 18" />
          <path className="dataset-svg__accent" d="M42 66H30l8 8" />
        </svg>
      );
    case 3:
      return (
        <svg className="dataset-card__svg" viewBox="0 0 160 120" aria-hidden="true">
          <rect className="dataset-svg__panel" x="32" y="38" width="56" height="38" rx="10" />
          <path className="dataset-svg__panel" d="M88 50h22l16 14v12H88Z" />
          <circle className="dataset-svg__wheel" cx="54" cy="86" r="10" />
          <circle className="dataset-svg__wheel" cx="106" cy="86" r="10" />
          <path className="dataset-svg__accent" d="M44 52h30M44 64h22M96 58h18" />
        </svg>
      );
    case 4:
      return (
        <svg className="dataset-card__svg" viewBox="0 0 160 120" aria-hidden="true">
          <path className="dataset-svg__panel" d="M80 22l48 20-48 20-48-20Z" />
          <path className="dataset-svg__panel" d="M56 54h48v12c0 8-11 14-24 14s-24-6-24-14Z" />
          <path className="dataset-svg__outline" d="M56 54h48" />
          <path className="dataset-svg__outline" d="M128 42v28" />
          <circle className="dataset-svg__badge" cx="128" cy="78" r="6" />
        </svg>
      );
    default:
      return (
        <svg className="dataset-card__svg" viewBox="0 0 160 120" aria-hidden="true">
          <circle className="dataset-svg__badge" cx="50" cy="44" r="12" />
          <circle className="dataset-svg__badge" cx="110" cy="44" r="12" />
          <circle className="dataset-svg__badge" cx="80" cy="76" r="12" />
          <path className="dataset-svg__outline" d="M50 56l30 16 30-16" />
          <path className="dataset-svg__outline" d="M50 32l30 18 30-18" />
          <path className="dataset-svg__accent" d="M80 58v10" />
        </svg>
      );
  }
}

function GenerateVisual() {
  const { containerRef, phase } = useViewportPhaseSequence({
    initialPhase: "screen",
    steps: GENERATE_PHASE_STEPS,
    threshold: 0.16,
  });

  return (
    <div ref={containerRef} className={`marketing-visual simple-scene simple-scene--generate phase-${phase}`}>
      <svg className="simple-scene__svg" viewBox="0 0 460 320" aria-hidden="true">
        <g className="simple-generate__computer">
          <rect className="simple-generate__monitor" x="104" y="64" width="252" height="154" rx="28" />
          <rect className="simple-generate__screen" x="124" y="84" width="212" height="114" rx="18" />
          <rect className="simple-generate__stand" x="210" y="218" width="40" height="26" rx="13" />
          <rect className="simple-generate__base" x="176" y="242" width="108" height="18" rx="9" />

          <g className="simple-generate__screen-docs">
            <g transform="translate(176 142) scale(0.42)">
              <g className="simple-generate__screen-doc simple-generate__screen-doc--1">
                <SceneDocument accent="blue" />
              </g>
            </g>
            <g transform="translate(230 130) scale(0.42)">
              <g className="simple-generate__screen-doc simple-generate__screen-doc--2">
                <SceneDocument accent="green" />
              </g>
            </g>
            <g transform="translate(284 142) scale(0.42)">
              <g className="simple-generate__screen-doc simple-generate__screen-doc--3">
                <SceneDocument accent="red" />
              </g>
            </g>
          </g>
        </g>

        <g transform="translate(230 150)" className="simple-generate__hero-files">
          <g>
            <g className="simple-generate__hero-file simple-generate__hero-file--1">
              <SceneDocument accent="blue" />
            </g>
          </g>
          <g>
            <g className="simple-generate__hero-file simple-generate__hero-file--2">
              <SceneDocument accent="green" />
            </g>
          </g>
          <g>
            <g className="simple-generate__hero-file simple-generate__hero-file--3">
              <SceneDocument accent="red" />
            </g>
          </g>
        </g>
      </svg>
    </div>
  );
}

function AnonymizeVisual() {
  const { containerRef, phase } = useViewportPhaseSequence({
    initialPhase: "raw",
    steps: ANONYMIZE_PHASE_STEPS,
    threshold: 0.16,
  });

  return (
    <div ref={containerRef} className={`marketing-visual simple-scene simple-scene--anonymize phase-${phase}`}>
      <svg className="simple-scene__svg" viewBox="0 0 460 320" aria-hidden="true">
        <rect className="simple-anonymize__panel" x="56" y="112" width="348" height="96" rx="28" />
        <text className="simple-anonymize__text simple-anonymize__text--raw" x="230" y="172" textAnchor="middle">
          your_mail@example.com
        </text>
        <text className="simple-anonymize__text simple-anonymize__text--masked" x="230" y="172" textAnchor="middle">
          y***l@example.com
        </text>
        <path className="simple-anonymize__accent" d="M104 136H356" />
      </svg>
    </div>
  );
}

function SimilarVisual() {
  const { containerRef, phase } = useViewportPhaseSequence({
    initialPhase: "single",
    steps: SIMILAR_PHASE_STEPS,
    threshold: 0.16,
  });

  return (
    <div ref={containerRef} className={`marketing-visual simple-scene simple-scene--similar phase-${phase}`}>
      <svg className="simple-scene__svg" viewBox="0 0 460 320" aria-hidden="true">
        <ellipse className="simple-similar__glow" cx="230" cy="228" rx="132" ry="44" />

        <g transform="translate(230 160)">
          <g className="simple-similar__source">
            <SceneDocument accent="blue" />
          </g>
        </g>

        <g transform="translate(230 160)">
          <g className="simple-similar__clone simple-similar__clone--left">
            <SceneDocument accent="blue" />
          </g>
        </g>

        <g transform="translate(230 160)">
          <g className="simple-similar__clone simple-similar__clone--right">
            <SceneDocument accent="blue" />
          </g>
        </g>

        <path className="simple-similar__trail simple-similar__trail--left" d="M220 164c-12 2-24 10-38 24" />
        <path className="simple-similar__trail simple-similar__trail--right" d="M240 164c12 2 24 10 38 24" />
      </svg>
    </div>
  );
}

export function LandingPage() {
  const { language } = useLanguage();
  const t = content[language];

  const visuals = [<GenerateVisual key="generate" />, <AnonymizeVisual key="anonymize" />, <SimilarVisual key="similar" />];

  return (
    <main className="page-root">
      <section className="hero">
        <div className="hero__background">
          <DotGridBackground />
        </div>
        <div className="hero__overlay" />
        <div className="page-container hero__content">
          <p className="eyebrow">{t.heroEyebrow}</p>
          <h1 className="hero__title">{t.heroTitle}</h1>
          <p className="hero__description">{t.heroDescription}</p>
          <div className="hero__actions">
            <Link href="/generate" className="button button--primary">
              {t.heroPrimary}
            </Link>
            <a href="#how-it-works" className="button button--ghost">
              {t.heroSecondary}
            </a>
          </div>
        </div>
      </section>

      <div className="page-container">
        {t.sections.map((section, index) => (
          <Reveal key={section.href}>
            <section className="marketing-section">
              <div className="marketing-copy">
                <p className="eyebrow">{section.tag}</p>
                <h2>{section.title}</h2>
                <p>{section.description}</p>
                <Link href={section.href} className="button button--secondary">
                  {section.action}
                </Link>
              </div>
              <div className="marketing-media">{visuals[index]}</div>
            </section>
          </Reveal>
        ))}

        <Reveal>
          <section id="how-it-works" className="knowledge-section">
            <div className="knowledge-section__header">
              <h2>{t.howItWorksTitle}</h2>
            </div>
            <div className="knowledge-grid">
              {t.howItWorksSteps.map((item) => (
                <article key={item.title} className="knowledge-card">
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </article>
              ))}
            </div>
          </section>
        </Reveal>

        <Reveal>
          <section className="knowledge-section knowledge-section--datasets">
            <div className="knowledge-section__header">
              <h2>{t.datasetsTitle}</h2>
              <p>{t.datasetsDescription}</p>
            </div>
            <div className="dataset-grid">
              {t.datasets.map((item, index) => (
                <article key={item} className={`dataset-card dataset-card--${index + 1}`}>
                  <div className="dataset-card__glow" />
                  <div className="dataset-card__visual">
                    <DatasetIllustration index={index} />
                  </div>
                  <strong>{item}</strong>
                </article>
              ))}
            </div>
          </section>
        </Reveal>
      </div>
    </main>
  );
}
