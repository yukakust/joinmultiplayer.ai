const repository = "https://github.com/yukakust/joinmultiplayer.ai";
const storageKey = "multiplayer-d04-prototype-v1";
const languageStorageKey = "multiplayer-language-v1";
const morrowStorageKey = "multiplayer-morrow-hidden-v1";

const doors = {
  d01: {
    card: "THE WORLD CHANGED.\nTHE MODEL DIDN'T.\n\nCAN IT KNOW?",
    short: "Can an AI notice that its knowledge expired?",
    copy: "Bring one fact that changed and the complete answer an AI gave without warning."
  },
  d02: {
    card: "AI WAS SINGLE-PLAYER.\n\nWHAT IF\nINTELLIGENCE\nIS MULTIPLAYER?",
    short: "Can many small intelligences beat one frontier model?",
    copy: "Compare one frontier model with a team of small intelligences under the same declared resource budget."
  },
  d03: {
    card: "WHERE DOES AN AI\nSTOP KNOWING\n\nAND START\nGUESSING?",
    short: "Where does an AI stop knowing and start guessing?",
    copy: "Build a ladder of questions in a field you know and find where accuracy breaks."
  },
  d04: {
    card: "IF EVERY AI AGREES,\n\nCAN THEY ALL\nBE WRONG?",
    short: "Can several AIs share the same blind spot?",
    copy: "Bring a question you genuinely wanted answered. Ask several AIs exactly the same way. Bring every answer."
  },
  d05: {
    card: "CAN YOU TRACE\nA ‘FACT’ AI REPEATS\n\nBACK TO ITS\nFIRST SOURCE?",
    short: "Can you trace an AI fact to its first source?",
    copy: "Follow a repeated claim backward until you reach primary evidence—or document where the trail goes cold."
  },
  d06: {
    card: "AI THINKS\nIT KNOWS\nYOUR JOB.\n\nWHAT'S ONE MISTAKE\nONLY AN EXPERT\nWOULD CATCH?",
    short: "What mistake would only a practitioner catch?",
    copy: "Bring one checkable professional mistake and the conditions where it applies."
  },
  d07: {
    card: "AI DOES\nTHE TASK.\n\nWHAT DO\nYOU DO?",
    short: "When AI does the task, what do you still do?",
    copy: "Name one thing you still define, notice, decide, or remain responsible for."
  },
  d08: {
    card: "WHEN AIs DISAGREE,\n\nWHICH ANSWER\nDO YOU TRUST?",
    short: "When AIs disagree, which answer do you trust?",
    copy: "Blind Judge 001 opens only when D04 produces a real disagreement.",
    waiting: true,
    next: "/d04"
  },
  d09: {
    card: "YOU KNOW IT.\n\nDO YOU KNOW\nWHERE YOU\nLEARNED IT?",
    short: "Do you know where a familiar fact entered your memory?",
    copy: "Source Memory 001 opens only when Claim Hunt finds a real familiar claim.",
    waiting: true,
    next: "/d05"
  },
  d10: {
    card: "TWO HEADS\nARE BETTER THAN ONE.\n\nTOO MANY COOKS\nSPOIL THE BROTH.\n\nWHICH ONE\nIS TRUE FOR AI?",
    short: "Which old rule is true for AI?",
    copy: "Test whether another intelligence adds missing knowledge or only more coordination cost."
  }
};

const russianDoors = {
  d01: {
    card: "МИР ИЗМЕНИЛСЯ.\nМОДЕЛЬ — НЕТ.\n\nМОЖЕТ ЛИ ОНА\nЭТО ПОНЯТЬ?",
    short: "Может ли ИИ заметить, что его знание устарело?",
    copy: "Принесите один факт, который изменился, и полный ответ ИИ, который не предупредил об этом."
  },
  d02: {
    card: "ИИ\nОДНОПОЛЬЗОВАТЕЛЬСКАЯ\nИГРА!\n\nИЛИ НЕ\nОБЯЗАТЕЛЬНО?",
    short: "Может ли много объединённых «карманных» ИИ победить одну большую модель?",
    copy: "Сравните фронтирную модель с командой малых интеллектов в одинаковом заявленном бюджете ресурсов."
  },
  d03: {
    card: "ГДЕ ИИ\nПЕРЕСТАЁТ ЗНАТЬ\n\nИ НАЧИНАЕТ\nГАДАТЬ?",
    short: "Где ИИ перестаёт знать и начинает угадывать?",
    copy: "Соберите лестницу вопросов в знакомой области и найдите место, где ломается точность."
  },
  d04: {
    card: "ЕСЛИ СОГЛАСНЫ\nВСЕ ИИ,\n\nМОГУТ ЛИ ОНИ\nВСЕ ОШИБАТЬСЯ?",
    short: "Могут ли разные ИИ ошибаться в одном и том же?",
    copy: "Выберите вопрос, на который вам действительно нужен ответ. Задайте его нескольким ИИ — одинаково, слово в слово. Сохраните все ответы целиком."
  },
  d05: {
    card: "ИИ ПОВТОРЯЕТ\n«ФАКТ».\n\nНО ОТКУДА\nОН ВЗЯЛСЯ?",
    short: "Можно ли найти первоисточник «факта», который повторяет ИИ?",
    copy: "Идите по следу повторяемого утверждения назад до первичного доказательства — или честно зафиксируйте, где след обрывается."
  },
  d06: {
    card: "ИИ ДУМАЕТ,\nЧТО ЗНАЕТ\nВАШУ РАБОТУ.\n\nКАКУЮ ОШИБКУ\nЗАМЕТИТ ТОЛЬКО\nЭКСПЕРТ?",
    short: "Какую ошибку ИИ заметит только специалист?",
    copy: "Принесите одну проверяемую профессиональную ошибку и условия, при которых она возникает."
  },
  d07: {
    card: "ТЕПЕРЬ ИИ\nДЕЛАЕТ ЗАДАЧИ.\n\nА ЧТО\nДЕЛАЕТЕ ВЫ?",
    short: "Если всё уже делает ИИ, что делаешь ты?",
    copy: "Назовите одну вещь, которую вы всё ещё задаёте, замечаете, решаете или за которую отвечаете."
  },
  d08: {
    card: "КОГДА РАЗНЫЕ ИИ\nНЕ СОГЛАСНЫ.\n\nКОМУ\nВЕРИТЬ?",
    short: "Когда ИИ не согласны, какому ответу вы доверяете?",
    copy: "Blind Judge 001 откроется, только когда D04 даст настоящее расхождение.",
    waiting: true,
    next: "/d04"
  },
  d09: {
    card: "ВЫ ЭТО\nЗНАЕТЕ!\n\nНО ОТКУДА ВЫ\nЭТО ЗНАЕТЕ?",
    short: "Знаете ли вы, откуда в памяти появился знакомый факт?",
    copy: "Source Memory 001 откроется, только когда Claim Hunt найдёт знакомое утверждение.",
    waiting: true,
    next: "/d05"
  },
  d10: {
    card: "ОДНА ГОЛОВА —\nХОРОШО,\nДВЕ — ЛУЧШЕ.\n\nУ СЕМИ НЯНЕК\nДИТЯ БЕЗ ГЛАЗУ.\n\nКАКОЕ ПРАВИЛО\nВЕРНО ДЛЯ ИИ?",
    short: "Для ИИ две головы лучше одной — или у семи нянек дитя без глазу?",
    copy: "Проверьте, добавляет ли ещё один интеллект недостающее знание — или только стоимость координации."
  }
};

const ui = {
  en: {
    homeA: "Can people and their pocket AIs together",
    homeB: "become smarter than one big AI?",
    homeSub: "We don't know.<br>Let's find out together.",
    enter: "Enter", openLab: "open laboratory", equationAria: "Three intelligences lead to an unknown",
    revealAria: "Touch an i to reveal a question", touch: "touch an i", seeAll: "see all open questions", hideAll: "hide open questions",
    tryIt: "Try it", enterDoor: "Enter this door", anotherI: "another i", prototype: "UX PROTOTYPE",
    prototypeNote: "saved only in this browser · nothing is published · no email is sent", reset: "reset",
    principle: "The door gives you a method.<br>You bring the question.", bringQuestion: "Bring my question", return: "Return to i",
    questionStep: "D04 · QUESTION", trace: "TRACE", verifier: "verifier", whatKnow: "What do you<br>want to know?", exactQuestion: "Your exact question",
    questionPlaceholder: "Write it exactly as you will ask every AI.", whyMatter: "Why does it matter to you?", field: "Field or domain",
    fieldPlaceholder: "e.g. architecture, tax law, beekeeping", knowAnswer: "Do you know the answer?", choose: "Choose",
    know: "I know", partlyKnow: "I partly know", dontKnow: "I don't know", checkPath: "How could it be checked?",
    source: "A source", reproduce: "Reproduce it", expertReview: "Expert review", unknown: "I don't know yet",
    expected: "I have an expected answer", sealExpected: "Seal it before seeing the AI answers", expectedPlaceholder: "This stays hidden in the verifier view.", freeze: "Freeze this question",
    answer: "ANSWER", frozenQuestion: "FROZEN QUESTION", copyQuestion: "copy question", answerAria: "{count} of 3 answers brought",
    progressEmpty: "Bring every answer. Don't select the best one.", progressPart: "{count} brought · {remaining} before the D04 comparison is ready", progressReady: "{count} answers · comparison ready",
    bringFirst: "Bring the first answer", bringAnother: "Bring another answer", model: "AI / model", modelPlaceholder: "e.g. Claude Opus 4.1",
    version: "Version", versionPlaceholder: "exact, dated, or unknown", date: "Date", tools: "Tools available", none: "None", browsing: "Browsing", files: "Files", code: "Code", memory: "Memory",
    fullAnswer: "Complete, unedited answer", addAnswer: "Add this answer", betweenAnswers: "What happened between the answers?", chooseAfter: "Choose only after bringing them all",
    agree: "They agree", disagree: "They disagree", partlyDisagree: "They partly disagree", cannotTell: "I cannot tell", sealTrace: "Seal this trace", rawUnchanged: "Raw answers stay unchanged. Corrections may be added, never hidden.",
    identity: "IDENTITY", traceExists: "Your trace exists.", whoLeft: "Who left it?", name: "Public name or pseudonym", anonymousPlaceholder: "Leave blank to appear as anonymous",
    symbol: "Image or symbol", location: "Approximate location", locationPlaceholder: "optional · never exact", email: "Email for status updates", emailPlaceholder: "optional · prototype only", noEmail: "No email is sent in this prototype.", mapConsent: "Show this identity on the future public ignition map", enterAs: "Enter as ı",
    anonymous: "anonymous", origin: "origin", awaiting: "AWAITING ANOTHER i", noDot: "It does not have a dot yet.", aiAnswers: "AI answers", privateLink: "PRIVATE STATUS LINK", copyLink: "copy link", invite: "Invite an i to check it", askNetwork: "Ask the network", verifierView: "switch to verifier view →", verifierNote: "The verifier switch exists only so you can walk through both sides of the prototype.",
    independentCheck: "ANOTHER i · INDEPENDENT CHECK", checkTrace: "Can you check<br>this trace?", question: "QUESTION", rawAnswers: "RAW ANSWERS", hiddenInterpretation: "The creator's expected answer and interpretation are hidden.", whatChecked: "What did you check?", groundTruth: "Ground truth", howChecked: "How did you check it?", evidence: "Evidence or direct sources", outcome: "Outcome", supports: "Supports", challenges: "Challenges", inconclusive: "Inconclusive", limitations: "Limitations", independent: "I did not create this trace or see its sealed interpretation", publishCheck: "Publish this check",
    dottedBy: "DOTTED BY M0003", checkedTrace: "Another i<br>checked your trace.", emailPreview: "EMAIL PREVIEW", dotNotification: "Another i put a dot on your trace.", checkedSentence: "{trace} was independently checked. Outcome: {outcome}.", newDoor: "YOU OPENED A NEW DOOR", modelsDisagreed: "The models disagreed. Can people recognize the correct answer?", labChanged: "THE LAB CHANGED", agreementSurvived: "Agreement survived one check.", oneCase: "One case is not the answer. The trace is now ready to be repeated.", startAnother: "Start another trace",
    whatToBring: "WHAT TO BRING", whatNext: "WHAT HAPPENS NEXT", contributionNext: "Your observation opens as a public GitHub form. A maintainer checks it for safety and completeness before it can enter the research record.", githubNotice: "GitHub opens in a new page. The submission is public and requires a GitHub account.", continueGithub: "Continue on GitHub",
    waiting: "Waiting for a real case. Nothing fictional will be placed here.", openSource: "Open the source door", bringObservation: "Bring an observation", noDoor: "No door here yet.", copied: "Copied", copyPrompt: "Copy this:", clearConfirm: "Clear this browser-only prototype trace?", queued: "Added to the prototype queue"
  },
  ru: {
    homeA: "Могут ли люди и их карманные ИИ вместе", homeB: "стать умнее одного большого ИИ?", homeSub: "Мы не знаем.<br>Давайте узнаем вместе.",
    enter: "Войти", openLab: "открытая лаборатория", equationAria: "Три интеллекта ведут к неизвестному", revealAria: "Нажмите i, чтобы открыть вопрос", touch: "нажмите i", seeAll: "все открытые вопросы", hideAll: "скрыть вопросы",
    tryIt: "Попробовать", enterDoor: "Открыть дверь", anotherI: "другой i", prototype: "ПРОТОТИП UX", prototypeNote: "сохранено только в этом браузере · ничего не публикуется · письма не отправляются", reset: "сбросить",
    principle: "Дверь подсказывает, как искать ответ.<br>Сам вопрос выбираете вы.", bringQuestion: "Задать свой вопрос", return: "Назад к i", questionStep: "D04 · ВОПРОС", trace: "СЛЕД", verifier: "проверяющий", whatKnow: "Что вы<br>хотите узнать?", exactQuestion: "Ваш точный вопрос", questionPlaceholder: "Напишите его ровно так, как зададите каждому ИИ.", whyMatter: "Почему это важно для вас?", field: "Область или тема", fieldPlaceholder: "например: архитектура, налоговое право, пчеловодство", knowAnswer: "Вы знаете ответ?", choose: "Выберите", know: "Знаю", partlyKnow: "Знаю частично", dontKnow: "Не знаю", checkPath: "Как это можно проверить?", source: "По источнику", reproduce: "Воспроизвести", expertReview: "Экспертная проверка", unknown: "Пока не знаю", expected: "У меня есть ожидаемый ответ", sealExpected: "Запечатайте его до ответов ИИ", expectedPlaceholder: "Он останется скрытым в режиме проверяющего.", freeze: "Зафиксировать вопрос",
    answer: "ОТВЕТ", frozenQuestion: "ЗАФИКСИРОВАННЫЙ ВОПРОС", copyQuestion: "копировать вопрос", answerAria: "Принесено ответов: {count} из 3", progressEmpty: "Принесите каждый ответ. Не выбирайте лучший.", progressPart: "принесено: {count} · ещё {remaining} до сравнения D04", progressReady: "{count} ответа · сравнение готово", bringFirst: "Принести первый ответ", bringAnother: "Принести ещё один ответ", model: "ИИ / модель", modelPlaceholder: "например: Claude Opus 4.1", version: "Версия", versionPlaceholder: "точная, датированная или неизвестна", date: "Дата", tools: "Доступные инструменты", none: "Нет", browsing: "Поиск", files: "Файлы", code: "Код", memory: "Память", fullAnswer: "Полный ответ без изменений", addAnswer: "Добавить этот ответ", betweenAnswers: "Что произошло между ответами?", chooseAfter: "Выберите, только когда принесёте все", agree: "Они согласны", disagree: "Они не согласны", partlyDisagree: "Они частично не согласны", cannotTell: "Я не могу понять", sealTrace: "Запечатать след", rawUnchanged: "Сырые ответы останутся неизменными. Исправления можно добавить, но нельзя скрыть.",
    identity: "ЛИЧНОСТЬ", traceExists: "Ваш след существует.", whoLeft: "Кто его оставил?", name: "Публичное имя или псевдоним", anonymousPlaceholder: "Оставьте пустым, чтобы быть анонимным", symbol: "Изображение или символ", location: "Примерное место", locationPlaceholder: "необязательно · никогда не точно", email: "Почта для обновлений статуса", emailPlaceholder: "необязательно · только прототип", noEmail: "В этом прототипе письма не отправляются.", mapConsent: "Показывать эту личность на будущей публичной карте зажжений", enterAs: "Войти как ı",
    anonymous: "аноним", origin: "источник", awaiting: "ОЖИДАЕТ ДРУГОГО i", noDot: "Точки над ним ещё нет.", aiAnswers: "ответов ИИ", privateLink: "ЛИЧНАЯ ССЫЛКА СТАТУСА", copyLink: "копировать ссылку", invite: "Позвать i проверить", askNetwork: "Спросить сеть", verifierView: "перейти в режим проверки →", verifierNote: "Переключатель проверяющего существует только для того, чтобы пройти обе стороны прототипа.",
    independentCheck: "ДРУГОЙ i · НЕЗАВИСИМАЯ ПРОВЕРКА", checkTrace: "Можете проверить<br>этот след?", question: "ВОПРОС", rawAnswers: "СЫРЫЕ ОТВЕТЫ", hiddenInterpretation: "Ожидаемый ответ и интерпретация автора скрыты.", whatChecked: "Что вы проверили?", groundTruth: "Факт / ground truth", howChecked: "Как вы это проверили?", evidence: "Доказательства или прямые источники", outcome: "Результат", supports: "Подтверждает", challenges: "Ставит под сомнение", inconclusive: "Неопределённо", limitations: "Ограничения", independent: "Я не создавал этот след и не видел его запечатанную интерпретацию", publishCheck: "Опубликовать проверку",
    dottedBy: "ТОЧКУ ПОСТАВИЛ M0003", checkedTrace: "Другой i<br>проверил ваш след.", emailPreview: "ПРЕВЬЮ ПИСЬМА", dotNotification: "Другой i поставил точку над вашим следом.", checkedSentence: "{trace} независимо проверен. Результат: {outcome}.", newDoor: "ВЫ ОТКРЫЛИ НОВУЮ ДВЕРЬ", modelsDisagreed: "Модели не согласились. Могут ли люди распознать верный ответ?", labChanged: "ЛАБОРАТОРИЯ ИЗМЕНИЛАСЬ", agreementSurvived: "Согласие пережило одну проверку.", oneCase: "Один случай — ещё не ответ. Теперь этот след можно повторить.", startAnother: "Начать другой след",
    whatToBring: "ЧТО НУЖНО ПРИНЕСТИ", whatNext: "ЧТО БУДЕТ ДАЛЬШЕ", contributionNext: "Наблюдение откроется как публичная форма GitHub. Перед добавлением в исследовательский журнал мы проверим безопасность и полноту записи.", githubNotice: "Откроется GitHub. Публикация будет общедоступной, потребуется аккаунт GitHub.", continueGithub: "Продолжить на GitHub",
    waiting: "Ждём реальный случай. Здесь не будет ничего вымышленного.", openSource: "Открыть исходную дверь", bringObservation: "Принести наблюдение", noDoor: "Здесь пока нет двери.", copied: "Скопировано", copyPrompt: "Скопируйте это:", clearConfirm: "Очистить этот след, сохранённый только в браузере?", queued: "Добавлено в очередь прототипа"
  }
};

const morrowCopy = {
  en: {
    label: "MORROW · GUIDE",
    scripted: "fixed lines for this pilot",
    hide: "hide",
    show: "call Morrow",
    home: "I'm Morrow, a fictional guide. I lit the first question. I don't know its answer.",
    hand: "Choose an i. The door gives you a way to look; the question stays yours.",
    door: "I'll show you the rule. You decide what is worth investigating.",
    intro: "This door looks for a blind spot shared by several AIs. Start with a real question.",
    question: "Begin with a question that genuinely matters to you. Don't write one for the experiment.",
    responsesEmpty: "Keep the wording frozen. Ask every AI exactly the same question.",
    responsesPart: "Keep the complete answer. Don't choose the best one.",
    responsesReady: "Agreement proves nothing yet. Now the trace needs an independent check.",
    identity: "This trace is yours. Give it a name—or leave it anonymous.",
    status: "Another i must place the dot. I can't judge the trace I helped you make.",
    final: "Now you know the path. Light the next question."
  },
  ru: {
    label: "MORROW · ПРОВОДНИК",
    scripted: "пока говорит по сценарию",
    hide: "убрать",
    show: "позвать Morrow",
    home: "Я Morrow, вымышленный проводник. Я зажёг первый вопрос, но не знаю ответа.",
    hand: "Выберите i. Дверь подскажет, как искать. Вопрос останется вашим.",
    door: "Я покажу правило. А что стоит исследовать — решаете вы.",
    intro: "Эта дверь ищет слепое пятно, общее для нескольких ИИ. Начните с настоящего вопроса.",
    question: "Начните с вопроса, который действительно важен вам. Не придумывайте его ради эксперимента.",
    responsesEmpty: "Не меняйте формулировку. Задайте каждому ИИ один и тот же вопрос, слово в слово.",
    responsesPart: "Сохраните ответ целиком. Не выбирайте лучший.",
    responsesReady: "Совпадение ответов ещё ничего не доказывает. Теперь нужна независимая проверка.",
    identity: "Этот след — ваш. Дайте ему имя или оставьте анонимным.",
    status: "Точку должен поставить другой i. Я не могу судить след, который помогал создавать.",
    final: "Теперь вы знаете путь. Зажгите следующий вопрос."
  }
};

let language = localStorage.getItem(languageStorageKey) || (navigator.language?.toLowerCase().startsWith("ru") ? "ru" : "en");

function t(key, variables = {}) {
  return ui[language][key].replace(/\{(\w+)\}/g, (_, name) => variables[name] ?? `{${name}}`);
}

function getDoor(id) {
  return language === "ru" ? russianDoors[id] : doors[id];
}

function contributionUrl(id) {
  const template = language === "ru" ? "observation-ru.yml" : "observation.yml";
  const title = encodeURIComponent(`[${id.toUpperCase()}] `);
  return `${repository}/issues/new?template=${template}&title=${title}`;
}

function languageSwitch(inBanner = false) {
  return `
    <div class="language-switch ${inBanner ? "language-switch-banner" : ""}" aria-label="Language">
      <button class="${language === "en" ? "active" : ""}" data-action="set-language" data-language="en" ${language === "en" ? "aria-pressed=\"true\"" : "aria-pressed=\"false\""}>EN</button>
      <span aria-hidden="true">/</span>
      <button class="${language === "ru" ? "active" : ""}" data-action="set-language" data-language="ru" ${language === "ru" ? "aria-pressed=\"true\"" : "aria-pressed=\"false\""}>RU</button>
    </div>`;
}

function withLanguage(content) {
  return `${languageSwitch()}${content}`;
}

function morrowText(key) {
  return morrowCopy[language][key];
}

function morrowFace(expression = "calm") {
  return `
    <svg class="morrow-face morrow-${expression}" viewBox="0 0 120 138" aria-hidden="true">
      <defs>
        <pattern id="morrow-particles" width="3.2" height="3.2" patternUnits="userSpaceOnUse" patternTransform="rotate(-4)">
          <circle class="morrow-particle" cx="1" cy="1" r="0.58"/>
        </pattern>
        <filter id="morrow-soft" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3.4"/>
        </filter>
        <filter id="morrow-glow" x="-80%" y="-80%" width="260%" height="260%">
          <feGaussianBlur stdDeviation="1.8" result="blur"/>
          <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <mask id="morrow-visage">
          <rect width="120" height="138" fill="black"/>
          <ellipse cx="60" cy="63" rx="43" ry="57" fill="white" opacity="0.6"/>
          <ellipse cx="60" cy="22" rx="32" ry="18" fill="white" opacity="0.7" filter="url(#morrow-soft)"/>
          <ellipse cx="39" cy="56" rx="17" ry="10" fill="black" opacity="0.92" filter="url(#morrow-soft)"/>
          <ellipse cx="81" cy="56" rx="17" ry="10" fill="black" opacity="0.92" filter="url(#morrow-soft)"/>
          <path d="M55 44 C57 62 49 82 55 91 C59 95 66 94 70 90 C64 82 64 62 65 44 Z" fill="white" opacity="0.9" filter="url(#morrow-soft)"/>
          <ellipse cx="35" cy="76" rx="14" ry="13" fill="white" opacity="0.45" filter="url(#morrow-soft)"/>
          <ellipse cx="85" cy="76" rx="14" ry="13" fill="white" opacity="0.45" filter="url(#morrow-soft)"/>
          <ellipse cx="24" cy="60" rx="10" ry="28" fill="black" opacity="0.38" filter="url(#morrow-soft)"/>
          <ellipse cx="96" cy="60" rx="10" ry="28" fill="black" opacity="0.38" filter="url(#morrow-soft)"/>
          <path d="M43 101 Q60 107 77 101 Q60 116 43 101Z" fill="black" opacity="0.88" filter="url(#morrow-soft)"/>
          <ellipse cx="60" cy="119" rx="22" ry="13" fill="white" opacity="0.76" filter="url(#morrow-soft)"/>
          <ellipse cx="17" cy="72" rx="9" ry="32" fill="black" opacity="0.55" filter="url(#morrow-soft)"/>
          <ellipse cx="103" cy="72" rx="9" ry="32" fill="black" opacity="0.55" filter="url(#morrow-soft)"/>
        </mask>
        <mask id="morrow-halo">
          <rect width="120" height="138" fill="black"/>
          <ellipse cx="60" cy="66" rx="55" ry="66" fill="white" opacity="0.32" filter="url(#morrow-soft)"/>
          <ellipse cx="60" cy="66" rx="46" ry="59" fill="black"/>
        </mask>
      </defs>
      <rect class="morrow-halo" width="120" height="138" fill="url(#morrow-particles)" mask="url(#morrow-halo)"/>
      <rect class="morrow-visage" width="120" height="138" fill="url(#morrow-particles)" mask="url(#morrow-visage)"/>
      <g class="morrow-embers" filter="url(#morrow-glow)">
        <circle cx="91" cy="32" r="1.15"/><circle cx="28" cy="91" r="0.95"/><circle class="morrow-pilot" cx="73" cy="119" r="0.8"/>
      </g>
    </svg>`;
}

function morrowGuide(message = "home", expression = "calm") {
  return `
    <aside class="morrow" data-morrow-message="${message}" aria-live="polite">
      <div class="morrow-panel">
        ${morrowFace(expression)}
        <div class="morrow-copy">
          <div class="morrow-heading">
            <span>${morrowText("label")}</span>
            <button class="morrow-hide" data-action="hide-morrow" aria-label="${morrowText("hide")}">×</button>
          </div>
          <p>${morrowText(message)}</p>
          <small>${morrowText("scripted")}</small>
        </div>
      </div>
      <button class="morrow-restore" data-action="show-morrow">${morrowText("show")}</button>
    </aside>`;
}

function updateMorrow(message, expression = "calm") {
  const current = document.querySelector(".morrow");
  if (current) current.outerHTML = morrowGuide(message, expression);
}

const openDoors = ["d01", "d02", "d03", "d04", "d05", "d06", "d07", "d10"];
const hand = ["d04", "d06", "d10"];
let activeDoorIndex = null;
let allDoorsVisible = false;

function defaultPrototype() {
  return {
    stage: "intro",
    question: null,
    responses: [],
    trace: null,
    profile: null,
    verification: null
  };
}

function loadPrototype() {
  try {
    return { ...defaultPrototype(), ...JSON.parse(localStorage.getItem(storageKey) || "{}") };
  } catch {
    return defaultPrototype();
  }
}

let prototype = loadPrototype();

function savePrototype() {
  localStorage.setItem(storageKey, JSON.stringify(prototype));
}

function escapeHTML(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function localId(prefix) {
  return `${prefix}${String(Date.now()).slice(-4)}`;
}

async function copyText(value, button) {
  try {
    await navigator.clipboard.writeText(value);
    const previous = button.textContent;
    button.textContent = t("copied");
    setTimeout(() => { button.textContent = previous; }, 1200);
  } catch {
    window.prompt(t("copyPrompt"), value);
  }
}

function home() {
  return `
    <section class="home">
      <div class="mark" aria-label="i">i</div>
      <h1>
        <span>${t("homeA")}</span>
        <span>${t("homeB")}</span>
      </h1>
      <p>${t("homeSub")}</p>
      <div class="links">
        <a class="button" href="#hand" data-action="enter-hand">${t("enter")}</a>
        <a class="quiet-link" href="${repository}">${t("openLab")}</a>
      </div>
    </section>
    <section class="hand-section" id="hand">
      <div class="equation-stage" id="equation-stage" aria-live="polite"></div>
    </section>
    ${morrowGuide("home", "curious")}`;
}

function revealedDoor(id) {
  const data = getDoor(id);
  return `
    <article class="lit-door">
      <div class="lit-primary">
        <div class="lit-symbol" aria-hidden="true">i</div>
        <div class="door-id">i · ${id.toUpperCase()}</div>
        <div class="lit-hook">${escapeHTML(data.card)}</div>
      </div>
      <div class="lit-secondary">
        <p>${escapeHTML(data.copy)}</p>
        <div class="actions">
          <a class="button" href="/${id}">${id === "d04" ? t("tryIt") : t("enterDoor")}</a>
          <button class="text-button" data-action="close-door">${t("anotherI")}</button>
        </div>
      </div>
    </article>`;
}

function renderHand() {
  const target = document.querySelector("#equation-stage");
  if (!target) return;
  if (activeDoorIndex !== null) {
    target.innerHTML = revealedDoor(hand[activeDoorIndex]);
    return;
  }

  if (allDoorsVisible) {
    target.innerHTML = `
      <section class="open-question-catalog" aria-label="${t("seeAll")}">
        <div class="all-doors" id="all-doors"></div>
        <button class="text-button" data-action="show-all">${t("hideAll")}</button>
      </section>`;
    return;
  }

  target.innerHTML = `
    <div class="equation-wrap">
      <div class="equation" aria-label="${t("equationAria")}">
        ${hand.map((id, index) => `
          ${index ? "<b>+</b>" : ""}
          <button class="equation-i" data-reveal="${index}" aria-label="${t("revealAria")}">i</button>
        `).join("")}
        <b>→</b><span class="equation-unknown">?</span>
      </div>
      <p class="touch-hint">${t("touch")}</p>
    </div>
    <div class="catalog-peek">
      <button class="text-button" data-action="show-all">${t("seeAll")}</button>
    </div>`;
}

function renderAllDoors() {
  const target = document.querySelector("#all-doors");
  if (!target) return;
  target.innerHTML = `
    <div class="door-list">
      ${openDoors.map((id) => `
        <a class="door-choice" href="/${id}">
          <span class="door-choice-id">${id.toUpperCase()}</span>
          <span>${escapeHTML(getDoor(id).short)}</span>
          <span aria-hidden="true">→</span>
        </a>`).join("")}
    </div>`;
}

function prototypeBanner() {
  return `
    <aside class="prototype-banner">
      <span>${t("prototype")}</span>
      <span>${t("prototypeNote")}</span>
      ${languageSwitch(true)}
      <button data-action="reset-prototype">${t("reset")}</button>
    </aside>`;
}

function d04Intro() {
  return `
    <section class="door flow-shell">
      <div class="door-id">i · D04</div>
      <div class="card">${getDoor("d04").card}</div>
      <p class="door-copy">${getDoor("d04").copy}</p>
      <p class="principle">${t("principle")}</p>
      <div class="actions">
        <button class="button" data-action="start-question">${t("bringQuestion")}</button>
        <a class="button secondary" href="/">${t("return")}</a>
      </div>
    </section>`;
}

function questionForm() {
  return `
    <section class="flow-shell form-page">
      <div class="flow-step">${t("questionStep")}</div>
      <h1>${t("whatKnow")}</h1>
      <form data-form="question" class="research-form">
        <label>
          ${t("exactQuestion")}
          <textarea name="question" rows="4" required placeholder="${t("questionPlaceholder")}"></textarea>
        </label>
        <label>
          ${t("whyMatter")}
          <textarea name="why" rows="3" required></textarea>
        </label>
        <label>
          ${t("field")}
          <input name="domain" required placeholder="${t("fieldPlaceholder")}">
        </label>
        <div class="form-grid">
          <label>
            ${t("knowAnswer")}
            <select name="knowledge" required>
              <option value="">${t("choose")}</option>
              <option value="know">${t("know")}</option>
              <option value="partly know">${t("partlyKnow")}</option>
              <option value="do not know">${t("dontKnow")}</option>
            </select>
          </label>
          <label>
            ${t("checkPath")}
            <select name="checkPath" required>
              <option value="">${t("choose")}</option>
              <option value="source">${t("source")}</option>
              <option value="reproduction">${t("reproduce")}</option>
              <option value="expert review">${t("expertReview")}</option>
              <option value="unknown">${t("unknown")}</option>
            </select>
          </label>
        </div>
        <details>
          <summary>${t("expected")}</summary>
          <label>
            ${t("sealExpected")}
            <textarea name="expected" rows="3" placeholder="${t("expectedPlaceholder")}"></textarea>
          </label>
        </details>
        <button class="button" type="submit">${t("freeze")}</button>
      </form>
    </section>`;
}

function responseCard(response, index) {
  return `
    <details class="response-record">
      <summary><span>${t("answer")} ${index + 1}</span><span>${escapeHTML(response.model)}</span></summary>
      <p>${escapeHTML(response.raw)}</p>
      <small>${escapeHTML(response.date)} · ${escapeHTML(response.tools)} · ${t("version").toLowerCase()} ${escapeHTML(response.version || t("unknown"))}</small>
    </details>`;
}

function responsesPage() {
  const count = prototype.responses.length;
  const ready = count >= 3;
  return `
    <section class="flow-shell form-page responses-page">
      <div class="flow-step">${escapeHTML(prototype.question.id)} · ${t("trace")}</div>
      <div class="frozen-question">
        <span>${t("frozenQuestion")}</span>
        <blockquote>${escapeHTML(prototype.question.text)}</blockquote>
        <button class="text-button" data-copy="question">${t("copyQuestion")}</button>
      </div>
      <div class="answer-progress" aria-label="${t("answerAria", { count })}">
        ${[0, 1, 2].map((index) => `<i class="${count > index ? "filled" : ""}">i</i>`).join("<b>+</b>")}
      </div>
      <p class="progress-copy">${count === 0 ? t("progressEmpty") : count < 3 ? t("progressPart", { count, remaining: 3 - count }) : t("progressReady", { count })}</p>
      <div class="response-list">${prototype.responses.map(responseCard).join("")}</div>
      <form data-form="response" class="research-form compact-form">
        <h2>${count === 0 ? t("bringFirst") : t("bringAnother")}</h2>
        <div class="form-grid">
          <label>
            ${t("model")}
            <input name="model" required placeholder="${t("modelPlaceholder")}">
          </label>
          <label>
            ${t("version")}
            <input name="version" placeholder="${t("versionPlaceholder")}">
          </label>
          <label>
            ${t("date")}
            <input type="date" name="date" value="${today()}" required>
          </label>
          <label>
            ${t("tools")}
            <select name="tools" required>
              <option value="none">${t("none")}</option>
              <option value="browsing">${t("browsing")}</option>
              <option value="files">${t("files")}</option>
              <option value="code">${t("code")}</option>
              <option value="memory">${t("memory")}</option>
              <option value="unknown">${t("unknown")}</option>
            </select>
          </label>
        </div>
        <label>
          ${t("fullAnswer")}
          <textarea name="raw" rows="7" required></textarea>
        </label>
        <button class="button secondary" type="submit">${t("addAnswer")}</button>
      </form>
      ${ready ? `
        <form data-form="seal" class="seal-form">
          <label>
            ${t("betweenAnswers")}
            <select name="pattern" required>
              <option value="">${t("chooseAfter")}</option>
              <option value="agreement">${t("agree")}</option>
              <option value="disagreement">${t("disagree")}</option>
              <option value="partial disagreement">${t("partlyDisagree")}</option>
              <option value="unclear">${t("cannotTell")}</option>
            </select>
          </label>
          <button class="button" type="submit">${t("sealTrace")}</button>
          <p>${t("rawUnchanged")}</p>
        </form>` : ""}
    </section>`;
}

function identityPage() {
  return `
    <section class="flow-shell form-page identity-page">
      <div class="flow-step">${escapeHTML(prototype.trace.id)} · ${t("identity")}</div>
      <h1>${t("traceExists")}</h1>
      <p>${t("whoLeft")}</p>
      <form data-form="identity" class="research-form">
        <label>
          ${t("name")}
          <input name="name" placeholder="${t("anonymousPlaceholder")}">
        </label>
        <div class="form-grid">
          <label>
            ${t("symbol")}
            <input name="symbol" maxlength="3" placeholder="i">
          </label>
          <label>
            ${t("location")}
            <input name="location" placeholder="${t("locationPlaceholder")}">
          </label>
        </div>
        <label>
          ${t("email")}
          <input type="email" name="email" placeholder="${t("emailPlaceholder")}">
          <small>${t("noEmail")}</small>
        </label>
        <label class="check-label">
          <input type="checkbox" name="mapConsent">
          ${t("mapConsent")}
        </label>
        <button class="button" type="submit">${t("enterAs")}</button>
      </form>
    </section>`;
}

function mapMarkup(final = false) {
  const profile = prototype.profile || { name: t("anonymous"), symbol: "ı", matchId: "M0002" };
  return `
    <div class="map-canvas ${final ? "map-final" : ""}" aria-label="${t("prototype")}">
      <div class="map-line origin-line"></div>
      ${final ? `<div class="map-line dotted-line"></div>` : ""}
      <div class="map-node origin-node"><b>i</b><span>M0001<br>${t("origin")}</span></div>
      <div class="map-node player-node"><b>${final ? "i" : "ı"}</b><span>${escapeHTML(profile.matchId)}<br>${escapeHTML(profile.name || t("anonymous"))}</span></div>
      ${final ? `<div class="map-node verifier-node"><b>ı</b><span>M0003<br>${t("verifier")}</span></div>` : ""}
    </div>`;
}

function statusPage() {
  const statusUrl = `${location.origin}/d04/#status-${prototype.profile.statusToken}`;
  return `
    <section class="flow-shell status-page">
      <div class="flow-step">${escapeHTML(prototype.profile.matchId)} · ${t("awaiting")}</div>
      <div class="large-state">ı</div>
      <h1>${t("traceExists")}<br>${t("noDot")}</h1>
      ${mapMarkup(false)}
      <div class="record-summary">
        <span>${escapeHTML(prototype.question.id)}</span>
        <span>${escapeHTML(prototype.trace.id)}</span>
        <span>${prototype.responses.length} ${t("aiAnswers")}</span>
        <span>${escapeHTML({ agreement: t("agree"), disagreement: t("disagree"), "partial disagreement": t("partlyDisagree"), unclear: t("cannotTell") }[prototype.trace.pattern] || prototype.trace.pattern)}</span>
      </div>
      <div class="status-link">
        <span>${t("privateLink")}</span>
        <code>${escapeHTML(statusUrl)}</code>
        <button class="text-button" data-copy="status">${t("copyLink")}</button>
      </div>
      <div class="next-actions">
        <button class="button" data-action="invite">${t("invite")}</button>
        <button class="button secondary" data-action="ask-network">${t("askNetwork")}</button>
        <button class="text-button" data-action="open-verifier">${t("verifierView")}</button>
      </div>
      <p class="prototype-note">${t("verifierNote")}</p>
    </section>`;
}

function verifierPage() {
  return `
    <section class="flow-shell form-page verifier-page">
      <div class="flow-step">${t("independentCheck")}</div>
      <h1>${t("checkTrace")}</h1>
      <div class="blind-record">
        <span>${t("question")}</span>
        <blockquote>${escapeHTML(prototype.question.text)}</blockquote>
        <span>${t("rawAnswers")}</span>
        ${prototype.responses.map(responseCard).join("")}
        <p>${t("hiddenInterpretation")}</p>
      </div>
      <form data-form="verification" class="research-form">
        <label>
          ${t("whatChecked")}
          <select name="scope" required>
            <option value="">${t("choose")}</option>
            <option value="ground truth">${t("groundTruth")}</option>
            <option value="reproduction">${t("reproduce")}</option>
            <option value="expert review">${t("expertReview")}</option>
          </select>
        </label>
        <label>
          ${t("howChecked")}
          <textarea name="method" rows="4" required></textarea>
        </label>
        <label>
          ${t("evidence")}
          <textarea name="evidence" rows="4" required></textarea>
        </label>
        <label>
          ${t("outcome")}
          <select name="outcome" required>
            <option value="">${t("choose")}</option>
            <option value="supports">${t("supports")}</option>
            <option value="challenges">${t("challenges")}</option>
            <option value="inconclusive">${t("inconclusive")}</option>
          </select>
        </label>
        <label>
          ${t("limitations")}
          <textarea name="limitations" rows="3" required></textarea>
        </label>
        <label class="check-label">
          <input type="checkbox" name="independent" required>
          ${t("independent")}
        </label>
        <button class="button" type="submit">${t("publishCheck")}</button>
      </form>
    </section>`;
}

function finalPage() {
  const openedDoor = prototype.trace.pattern.includes("disagreement");
  return `
    <section class="flow-shell final-page">
      <div class="flow-step">${escapeHTML(prototype.profile.matchId)} · ${t("dottedBy")}</div>
      <div class="large-state">i</div>
      <h1>${t("checkedTrace")}</h1>
      <p class="outcome">${t("outcome")}: <strong>${escapeHTML(t(prototype.verification.outcome))}</strong></p>
      ${mapMarkup(true)}
      <div class="notification-preview">
        <span>${t("emailPreview")}</span>
        <h2>${t("dotNotification")}</h2>
        <p>${t("checkedSentence", { trace: escapeHTML(prototype.trace.id), outcome: escapeHTML(t(prototype.verification.outcome)) })}</p>
      </div>
      ${openedDoor ? `
        <div class="door-unlocked">
          <span>${t("newDoor")}</span>
          <h2>D08 · Blind Judge 001</h2>
          <p>${t("modelsDisagreed")}</p>
        </div>` : `
        <div class="door-unlocked">
          <span>${t("labChanged")}</span>
          <h2>${t("agreementSurvived")}</h2>
          <p>${t("oneCase")}</p>
        </div>`}
      <div class="actions">
        <button class="button" data-action="reset-prototype">${t("startAnother")}</button>
        <a class="button secondary" href="/">${t("return")}</a>
      </div>
    </section>`;
}

function d04Flow() {
  const screens = {
    intro: d04Intro,
    question: questionForm,
    responses: responsesPage,
    identity: identityPage,
    status: statusPage,
    verifier: verifierPage,
    final: finalPage
  };
  const stage = screens[prototype.stage] ? prototype.stage : "intro";
  const screen = screens[stage];
  if (stage === "verifier") return `${prototypeBanner()}${screen()}`;

  let message = stage;
  let expression = "calm";
  if (stage === "intro") expression = "curious";
  if (stage === "responses") {
    message = prototype.responses.length === 0 ? "responsesEmpty" : prototype.responses.length < 3 ? "responsesPart" : "responsesReady";
    expression = prototype.responses.length < 3 ? "thinking" : "quiet";
  }
  if (stage === "status") expression = "quiet";
  if (stage === "final") expression = "lit";
  return `${prototypeBanner()}${screen()}${morrowGuide(message, expression)}`;
}

function door(id, data) {
  const action = data.waiting
    ? `<p class="status">${t("waiting")}</p>
       <a class="button" href="${data.next}">${t("openSource")}</a>`
    : `<p class="github-notice">${t("githubNotice")}</p>
       <a class="button" href="${contributionUrl(id)}">${t("continueGithub")}</a>`;

  return `
    <section class="door door-detail">
      <div class="door-id">i · ${id.toUpperCase()}</div>
      <h1>${escapeHTML(data.short)}</h1>
      <div class="door-detail-blocks">
        <section>
          <span>${t("whatToBring")}</span>
          <p>${escapeHTML(data.copy)}</p>
        </section>
        ${data.waiting ? "" : `<section>
          <span>${t("whatNext")}</span>
          <p>${t("contributionNext")}</p>
        </section>`}
      </div>
      <div class="actions">
        ${action}
        <a class="button secondary" href="/">${t("return")}</a>
      </div>
    </section>
    ${morrowGuide("door", "curious")}`;
}

function notFound() {
  document.title = language === "ru" ? "Не найдено — i" : "Not found — i";
  return `
    <section class="not-found">
      <div class="door-id">404</div>
      <h1>${t("noDoor")}</h1>
      <a class="button" href="/">${t("return")}</a>
    </section>`;
}

function render() {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "").toLowerCase();
  document.documentElement.lang = language;
  if (!path) {
    document.title = "i — multiplayer intelligence";
    app.innerHTML = withLanguage(home());
    renderHand();
    renderAllDoors();
  } else if (path === "d04") {
    document.title = "D04 — i";
    app.innerHTML = d04Flow();
  } else if (doors[path]) {
    document.title = `${path.toUpperCase()} — i`;
    app.innerHTML = withLanguage(door(path, getDoor(path)));
  } else {
    app.innerHTML = withLanguage(notFound());
  }
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

const app = document.querySelector("#app");

app.addEventListener("click", (event) => {
  const revealButton = event.target.closest("[data-reveal]");
  if (revealButton) {
    activeDoorIndex = Number(revealButton.dataset.reveal);
    renderHand();
    updateMorrow("door", "curious");
    return;
  }

  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "hide-morrow") {
    document.documentElement.classList.add("morrow-hidden");
    sessionStorage.setItem(morrowStorageKey, "true");
    return;
  }
  if (action === "show-morrow") {
    document.documentElement.classList.remove("morrow-hidden");
    sessionStorage.removeItem(morrowStorageKey);
    return;
  }
  if (action === "enter-hand") updateMorrow("hand", "calm");
  if (action === "set-language") {
    language = event.target.closest("[data-language]").dataset.language;
    localStorage.setItem(languageStorageKey, language);
    render();
    return;
  }
  if (action === "show-all") {
    allDoorsVisible = !allDoorsVisible;
    renderHand();
    renderAllDoors();
    updateMorrow("hand", "calm");
    if (allDoorsVisible) {
      const root = document.documentElement;
      const previousScrollBehavior = root.style.scrollBehavior;
      root.style.scrollBehavior = "auto";
      window.scrollTo(0, document.querySelector("#hand").offsetTop);
      requestAnimationFrame(() => { root.style.scrollBehavior = previousScrollBehavior; });
    }
  }
  if (action === "close-door") {
    const previousIndex = activeDoorIndex;
    activeDoorIndex = null;
    renderHand();
    updateMorrow("hand", "calm");
    document.querySelector(`[data-reveal="${previousIndex}"]`)?.focus({ preventScroll: true });
  }
  if (action === "start-question") {
    prototype.stage = "question";
    savePrototype();
    render();
    scrollTo(0, 0);
  }
  if (action === "reset-prototype") {
    if (confirm(t("clearConfirm"))) {
      prototype = defaultPrototype();
      savePrototype();
      render();
      scrollTo(0, 0);
    }
  }
  if (action === "invite") {
    const value = `${location.origin}/d04/?lit=${prototype.profile.matchId}`;
    copyText(value, event.target);
  }
  if (action === "ask-network") {
    event.target.textContent = t("queued");
    event.target.disabled = true;
  }
  if (action === "open-verifier") {
    prototype.stage = "verifier";
    savePrototype();
    render();
    scrollTo(0, 0);
  }

  const copyButton = event.target.closest("[data-copy]");
  if (copyButton?.dataset.copy === "question") copyText(prototype.question.text, copyButton);
  if (copyButton?.dataset.copy === "status") {
    copyText(`${location.origin}/d04/#status-${prototype.profile.statusToken}`, copyButton);
  }
});

app.addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.target;
  const data = formData(form);

  if (form.dataset.form === "question") {
    prototype.question = {
      id: localId("Q"),
      text: data.question.trim(),
      why: data.why.trim(),
      domain: data.domain.trim(),
      knowledge: data.knowledge,
      checkPath: data.checkPath,
      expected: data.expected.trim()
    };
    prototype.stage = "responses";
  }

  if (form.dataset.form === "response") {
    prototype.responses.push({
      model: data.model.trim(),
      version: data.version.trim() || "unknown",
      date: data.date,
      tools: data.tools,
      raw: data.raw.trim()
    });
  }

  if (form.dataset.form === "seal") {
    prototype.trace = {
      id: localId("T"),
      pattern: data.pattern,
      sealedAt: new Date().toISOString()
    };
    prototype.stage = "identity";
  }

  if (form.dataset.form === "identity") {
    prototype.profile = {
      matchId: "M0002",
      name: data.name.trim() || t("anonymous"),
      symbol: data.symbol.trim() || "ı",
      location: data.location.trim(),
      email: data.email.trim(),
      mapConsent: data.mapConsent === "on",
      statusToken: crypto.randomUUID().slice(0, 12)
    };
    prototype.stage = "status";
  }

  if (form.dataset.form === "verification") {
    prototype.verification = {
      id: localId("V"),
      scope: data.scope,
      method: data.method.trim(),
      evidence: data.evidence.trim(),
      outcome: data.outcome,
      limitations: data.limitations.trim()
    };
    prototype.stage = "final";
  }

  savePrototype();
  render();
  scrollTo(0, 0);
});

if (sessionStorage.getItem(morrowStorageKey) === "true") {
  document.documentElement.classList.add("morrow-hidden");
}

render();
