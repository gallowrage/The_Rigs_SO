const NOTE_NAMES = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"];
const CHORDS = {
  maj: { suffix: "", label: "MAJOR", intervals: [0, 4, 7] },
  min: { suffix: "m", label: "MINOR", intervals: [0, 3, 7] },
  6: { suffix: "6", label: "MAJOR 6", intervals: [0, 4, 7, 9] },
  min6: { suffix: "m6", label: "MINOR 6", intervals: [0, 3, 7, 9] },
  maj7: { suffix: "maj7", label: "MAJOR 7", intervals: [0, 4, 7, 11] },
  min7: { suffix: "m7", label: "MINOR 7", intervals: [0, 3, 7, 10] },
  7: { suffix: "7", label: "DOMINANT 7", intervals: [0, 4, 7, 10] },
  9: { suffix: "9", label: "DOMINANT 9", intervals: [0, 4, 7, 10, 14] },
  "7b9": { suffix: "7♭9", label: "DOMINANT 7 FLAT 9", intervals: [0, 4, 7, 10, 13] },
  13: { suffix: "13", label: "DOMINANT 13", intervals: [0, 4, 7, 10, 14, 21] },
  min9: { suffix: "m9", label: "MINOR 9", intervals: [0, 3, 7, 10, 14] },
  maj9: { suffix: "maj9", label: "MAJOR 9", intervals: [0, 4, 7, 11, 14] },
  11: { suffix: "11", label: "ELEVEN", intervals: [0, 4, 7, 10, 14, 17] },
  "7sus4": { suffix: "7sus4", label: "DOMINANT SUSPENDED 4", intervals: [0, 5, 7, 10] },
  m7b5: { suffix: "m7♭5", label: "HALF-DIMINISHED", intervals: [0, 3, 6, 10] },
  dim: { suffix: "dim", label: "DIMINISHED", intervals: [0, 3, 6] },
  aug: { suffix: "aug", label: "AUGMENTED", intervals: [0, 4, 8] },
  sus2: { suffix: "sus2", label: "SUSPENDED 2", intervals: [0, 2, 7] },
  sus4: { suffix: "sus4", label: "SUSPENDED 4", intervals: [0, 5, 7] },
  add9: { suffix: "add9", label: "ADD 9", intervals: [0, 4, 7, 14] },
};
const NOTE_TO_PC = Object.fromEntries(NOTE_NAMES.map((name, index) => [name, index]));
const FLAT_TO_PC = { "D♭": 1, "E♭": 3, "G♭": 6, "A♭": 8, "B♭": 10 };
const $ = (selector) => document.querySelector(selector);
const state = {
  generated: null,
  progression: [],
  detectedMidi: new Set(),
  detectedVelocity: 0.5,
  playStyle: "block",
  lastNoteTime: 0,
  audioContext: null,
  stream: null,
  animationFrame: null,
  midiAccess: null,
  midiInputs: [],
  micActive: false,
  toastTimer: null,
};

function noteName(pc) {
  return NOTE_NAMES[((pc % 12) + 12) % 12];
}

function selectedRoot() {
  const value = $("#root-select").value;
  return NOTE_TO_PC[value] ?? FLAT_TO_PC[value] ?? 0;
}

function chordName(root, quality) {
  return `${noteName(root)}${CHORDS[quality].suffix}`;
}

function makeVoicing(root, quality, inversion = 0, baseOctave = 3, style = "close") {
  let intervals = [...CHORDS[quality].intervals];
  if (style === "open" && intervals.length > 2) {
    intervals = intervals.map((interval, index) => index % 2 === 1 ? interval + 12 : interval);
  } else if (style === "spread" && intervals.length > 2) {
    intervals = intervals.map((interval, index) => index === 1 ? interval + 12 : index > 1 ? interval + 24 : interval);
  }
  const midi = intervals.map((interval) => 12 * (baseOctave + 1) + root + interval);
  const shift = Math.min(inversion, midi.length - 1);
  for (let index = 0; index < shift; index += 1) {
    midi[index] += 12;
  }
  return midi.sort((left, right) => left - right);
}

function renderKeyboard(target, activeMidi, velocity = 0.5) {
  const notes = [...activeMidi];
  let start = notes.length ? Math.floor(Math.min(...notes) / 12) * 12 : 48;
  const highest = notes.length ? Math.max(...notes) : start + 23;
  const octaves = Math.max(2, Math.ceil((highest - start + 1) / 12));
  
  const whiteNotes = [];
  for (let midi = start; midi < start + 12 * octaves; midi += 1) {
    if (![1, 3, 6, 8, 10].includes(midi % 12)) whiteNotes.push(midi);
  }
  const whiteIndex = new Map(whiteNotes.map((midi, index) => [midi, index]));
  target.replaceChildren();
  whiteNotes.forEach((midi) => {
    const key = document.createElement("span");
    key.className = `piano-key${activeMidi.has(midi) ? " active" : ""}`;
    if (activeMidi.has(midi)) key.style.setProperty("--vel", velocity);
    target.append(key);
  });
  const whiteCount = whiteNotes.length;
  for (let midi = start; midi < start + 12 * octaves; midi += 1) {
    if (![1, 3, 6, 8, 10].includes(midi % 12)) continue;
    const precedingWhite = whiteIndex.get(midi - 1);
    if (precedingWhite === undefined) continue;
    const key = document.createElement("span");
    key.className = `piano-key black${activeMidi.has(midi) ? " active" : ""}`;
    key.style.left = `${((precedingWhite + 1) / whiteCount) * 100}%`;
    key.style.width = `${(100 / whiteCount) * 0.62}%`;
    if (activeMidi.has(midi)) key.style.setProperty("--vel", velocity);
    target.append(key);
  }
}

let sampler = null;

async function initSampler() {
  if (!sampler) {
    await Tone.start();
    sampler = new Tone.Sampler({
      urls: {
        "A0": "A0.mp3",
        "C2": "C2.mp3",
        "D#3": "Ds3.mp3",
        "F#4": "Fs4.mp3",
        "A5": "A5.mp3",
        "C7": "C7.mp3",
      },
      release: 1.5,
      baseUrl: "https://tonejs.github.io/audio/salamander/"
    }).toDestination();
  }
}

async function playNotes(notes, duration = 1.15) {
  if (!window.Tone) {
    showToast("Tone.js hasn't loaded yet.");
    return;
  }
  await initSampler();
  if (!sampler.loaded) {
    showToast("Loading grand piano sounds...");
    await Tone.loaded();
  }
  
  const now = Tone.now();
  notes.forEach((midi, index) => {
    const frequency = Tone.Frequency(midi, "midi");
    // Arpeggiate slightly
    sampler.triggerAttackRelease(frequency, duration, now + index * 0.045, 0.8 - index * 0.05);
  });
}

function midiVariableLength(value) {
  const bytes = [value & 0x7f];
  while ((value >>= 7)) bytes.unshift((value & 0x7f) | 0x80);
  return bytes;
}

function midiBytes(value, length) {
  const bytes = [];
  for (let index = length - 1; index >= 0; index -= 1) bytes.push((value >> (index * 8)) & 0xff);
  return bytes;
}

function createMidiFile(chords, tempo = 92) {
  const ticksPerBeat = 480;
  const track = [
    ...[...new TextEncoder().encode("Chordcraft")].flatMap((byte, index) => index === 0 ? [0xff, 0x03, 10, byte] : [byte]),
    0, 0xff, 0x51, 3, ...midiBytes(Math.round(60000000 / tempo), 3),
  ];
  chords.forEach((notes) => {
    notes.forEach((note) => track.push(0, 0x90, note, 86));
    notes.forEach((note, index) => track.push(...midiVariableLength(index === 0 ? ticksPerBeat * 4 : 0), 0x80, note, 0));
  });
  track.push(0, 0xff, 0x2f, 0);
  return new Uint8Array([
    ...[...new TextEncoder().encode("MThd")], ...midiBytes(6, 4), ...midiBytes(0, 2),
    ...midiBytes(1, 2), ...midiBytes(ticksPerBeat, 2),
    ...[...new TextEncoder().encode("MTrk")], ...midiBytes(track.length, 4), ...track,
  ]);
}

function makeMidiDragData(chords, filename) {
  const bytes = createMidiFile(chords);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  const b64 = btoa(binary);
  return `audio/midi:${filename}:data:audio/midi;base64,${b64}`;
}

function setupMidiDraggable(buttonId, getChords, getFilename) {
  const btn = $(`#${buttonId}`);
  btn.draggable = true;
  btn.title = "Click to download, or drag to your DAW";
  btn.addEventListener("dragstart", (e) => {
    const chords = getChords();
    if (!chords || !chords.length) {
      e.preventDefault();
      return;
    }
    e.dataTransfer.setData("DownloadURL", makeMidiDragData(chords, getFilename()));
    e.dataTransfer.effectAllowed = "copy";
  });
}

function downloadMidi(chords, filename) {
  if (!chords?.length) {
    showToast("Create a chord or progression before exporting.");
    return;
  }
  const blob = new Blob([createMidiFile(chords)], { type: "audio/midi" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  showToast("MIDI downloaded.");
}

function updateGeneratedChord() {
  const root = selectedRoot();
  const quality = $("#quality-select").value;
  const inversion = Number($("#inversion-select").value);
  const voicing = $("#voicing-select").value;
  const notes = makeVoicing(root, quality, inversion, 3, voicing);
  state.generated = { root, quality, notes, voicing };
  $("#generated-name").textContent = chordName(root, quality);
  $("#generated-quality").textContent = `${CHORDS[quality].label}${inversion ? ` · ${inversion}${inversion === 1 ? "ST" : inversion === 2 ? "ND" : "RD"} INVERSION` : ""}`;
  $("#generated-notes").textContent = notes.map((midi) => noteName(midi % 12)).join(" · ");
  renderKeyboard($("#generator-keyboard"), new Set(notes));
  $("#progression-result").hidden = true;
}

const QUALITIES_BY_INTERVALS = [
  ["maj", [0, 4, 7]], ["min", [0, 3, 7]], ["dim", [0, 3, 6]],
  ["aug", [0, 4, 8]], ["sus2", [0, 2, 7]], ["sus4", [0, 5, 7]],
  ["6", [0, 4, 7, 9]], ["min6", [0, 3, 7, 9]],
  ["7", [0, 4, 7, 10]], ["maj7", [0, 4, 7, 11]], ["min7", [0, 3, 7, 10]],
  ["9", [0, 4, 7, 10, 14]], ["7b9", [0, 4, 7, 10, 13]],
  ["min9", [0, 3, 7, 10, 14]], ["maj9", [0, 4, 7, 11, 14]],
  ["13", [0, 4, 7, 10, 14, 21]], ["11", [0, 4, 7, 10, 14, 17]],
  ["7sus4", [0, 5, 7, 10]],
  ["m7b5", [0, 3, 6, 10]], ["add9", [0, 2, 4, 7]],
];

function identifyChord(midiNotes) {
  const pitchClasses = [...new Set(midiNotes.map((midi) => midi % 12))].sort((a, b) => a - b);
  if (pitchClasses.length < 3) return null;
  let best = null;
  for (let root = 0; root < 12; root += 1) {
    const intervals = pitchClasses.map((pc) => (pc - root + 12) % 12);
    for (const [quality, expected] of QUALITIES_BY_INTERVALS) {
      const matched = expected.filter((interval) => intervals.includes(interval % 12)).length;
      const extras = intervals.filter((interval) => !expected.some((value) => value % 12 === interval)).length;
      const score = matched / expected.length - extras * 0.16;
      if (matched >= 3 && (!best || score > best.score)) best = { root, quality, score, pitchClasses };
    }
  }
  return best && best.score >= 0.68 ? best : null;
}

function getEnhancements(chord, mood, velocity = 0.5, playStyle = "block") {
  const { root, quality } = chord;
  const base = CHORDS[quality].intervals;
  const isMinor = quality.startsWith("min") || quality === "m7b5" || quality === "dim";
  let choices = mood === "simple"
    ? [{ title: "Add a sixth", tag: "SOFT LIFT", intervals: [...base, 9], copy: "A gentle, familiar lift without changing the chord’s mood." },
      { title: "Add a ninth", tag: "OPEN", intervals: [...base, 14], copy: "One extra note gives the harmony a little more air." },
      { title: "Open voicing", tag: "SPACIOUS", intervals: [0, isMinor ? 3 : 4, 19], copy: "Spread the chord out for a lighter, more open sound." }]
    : mood === "jazzy"
      ? [{ title: "Add a 9th", tag: "SMOOTH", intervals: [...base, 14], copy: "A classic color tone that keeps the original chord at heart." },
        { title: "Add a 13th", tag: "RICH", intervals: [...base, 14, 21], copy: "A full, jazzy voicing with a warm top note." },
        { title: "Add a 7th", tag: "BLUE NOTE", intervals: [...base, isMinor ? 10 : 11], copy: "A seventh adds a little pull and a more soulful feel." }]
      : mood === "cinematic"
        ? [{ title: "Add a 9th", tag: "WIDE SCREEN", intervals: [...base, 14], copy: "A glowing top note makes the harmony feel expansive." },
          { title: "Open fifths", tag: "GRAND", intervals: [0, 7, 12, isMinor ? 15 : 16], copy: "An octave-spanning shape with a big, steady foundation." },
          { title: "Add a 6th", tag: "NOSTALGIC", intervals: [...base, 9], copy: "A little bittersweet color for a more reflective sound." }]
        : [{ title: "Add a 9th", tag: "LUSH", intervals: [...base, 14], copy: "A bright, floating color tone sits beautifully above your chord." },
          { title: "Add a 6th", tag: "WARM", intervals: [...base, 9], copy: "A soft, warm note that adds richness without crowding the sound." },
          { title: "Add a 7th", tag: "SOULFUL", intervals: [...base, isMinor ? 10 : 11], copy: "A gentle seventh adds a little extra emotional pull." }];

  const isSoft = velocity < 0.45;
  const isLoud = velocity > 0.75;
  if (isSoft && playStyle === "arpeggio") {
    choices[0] = { title: "Spread 9th", tag: "DREAMY", intervals: [0, 7, 14, isMinor ? 15 : 16], copy: "Since you're playing softly and rolling the chord, this spread voicing gives each note space to breathe." };
  } else if (isLoud && playStyle === "block") {
    choices[0] = { title: "Punchy 7th", tag: "DRIVING", intervals: [0, isMinor ? 3 : 4, 7, isMinor ? 10 : 11, 12], copy: "You played with force! This close, stacked voicing creates a dense, bright impact." };
  } else if (isSoft) {
    choices.forEach(c => c.tag = "INTIMATE " + c.tag);
    choices[2] = { title: "Wide & Open", tag: "ETHEREAL", intervals: [0, 7, 12, isMinor ? 15 : 16, 19], copy: "A delicate, wide voicing that responds beautifully to soft playing." };
  } else if (isLoud) {
    choices.forEach(c => c.tag = "BRIGHT " + c.tag);
    choices[2] = { title: "Clustered", tag: "DENSE", intervals: [...base, 14, 17].map(x => x % 12).sort((a,b) => a - b), copy: "A clustered, punchy shape that matches your aggressive dynamic." };
  }

  const hasSeventh = base.some((interval) => [10, 11].includes(interval % 12));
  if (hasSeventh) {
    choices.forEach((choice, index) => {
        if (choice.title.includes("7th") && !choice.title.includes("Punchy")) {
          choices[index] = { title: "Add a 6th", tag: "WARM", intervals: [...base, 9], copy: "A soft sixth adds warmth without stacking another seventh." };
        }
    });
  }
  const filteredChoices = choices.filter((choice, index) => {
    const addsANote = choice.intervals.some((interval) => !base.includes(interval));
    const duplicatesEarlierChoice = choices.slice(0, index).some((earlier) => JSON.stringify([...new Set(earlier.intervals)].sort((a, b) => a - b)) === JSON.stringify([...new Set(choice.intervals)].sort((a, b) => a - b)));
    return addsANote && !duplicatesEarlierChoice;
  });
  if (filteredChoices.length < 3) {
    filteredChoices.push({ title: "Open voicing", tag: "SPACIOUS", intervals: [0, isMinor ? 3 : 4, 19], copy: "Spread the chord across octaves for a more open sound." });
  }

  const isDominant = quality === "7" || quality === "9" || quality === "13" || quality === "7b9" || quality === "11" || quality === "7sus4";
  const isMajor = quality.startsWith("maj") || quality === "6" || quality === "add9" || quality === "aug" || quality === "maj";
  
  if (isDominant) {
    const tritoneRoot = (root + 6) % 12;
    filteredChoices.push({
      title: "Tritone Sub",
      tag: "SPICY (JAZZ)",
      intervals: [6, 10, 13, 16],
      copy: "Swap this dominant chord for a 7th chord a tritone away. Resolves down a half-step.",
      fixedName: `${noteName(tritoneRoot)}7 (Sub)`
    });
  } else if (isMajor) {
    filteredChoices.push({
      title: "Borrowed Minor 9",
      tag: "MODAL MIXTURE",
      intervals: [0, 3, 7, 10, 14],
      copy: "Borrow the parallel minor from the dark side. It gives a sudden, moody emotional shift.",
      fixedName: `${noteName(root)}min9 (Borrowed)`
    });
    const mediantRoot = (root + 8) % 12;
    filteredChoices.push({
      title: "Chromatic Mediant",
      tag: "CINEMATIC SHIFT",
      intervals: [8, 12, 15, 19],
      copy: "Jump to a major chord a major third down. Huge, dramatic, and beloved by film composers.",
      fixedName: `${noteName(mediantRoot)}maj (Mediant)`
    });
  } else if (isMinor) {
    filteredChoices.push({
      title: "Picardy Third",
      tag: "UPLIFTING",
      intervals: [0, 4, 7, 11, 14],
      copy: "Turn this minor chord suddenly bright. A classic classical-era trick to end on a hopeful note.",
      fixedName: `${noteName(root)}maj9 (Picardy)`
    });
  }

  return filteredChoices.slice(0, 4).map((choice) => {
    const intervals = [...new Set(choice.intervals)];
    const rootLabel = noteName(root);
    const baseName = chordName(root, quality);
    const name = choice.fixedName || (choice.title.includes("9th") ? `${baseName}add9`
          : choice.title.includes("13th") ? quality === "7" ? `${rootLabel}13` : quality === "maj7" ? `${rootLabel}maj13` : quality === "min7" ? `${rootLabel}m13` : `${rootLabel}${isMinor ? "m" : ""}6/9`
          : choice.title.includes("6th") ? `${baseName}add6`
          : choice.title.includes("7th") ? `${rootLabel}${({ maj: "maj7", min: "m7", dim: "m7♭5", aug: "augmaj7", sus2: "7sus2", sus4: "7sus4", add9: "maj9" }[quality] || "m7♭5")}`
          : choice.title.includes("fifths") || choice.title.includes("Spread") || choice.title.includes("Wide") || choice.title.includes("Clustered") ? `${baseName} · alt` : `${baseName} · open`);
    return { ...choice, name, notes: intervals.map((interval) => 48 + root + interval) };
  });
}

function updateDetected() {
  const midiNotes = [...state.detectedMidi].sort((a, b) => a - b);
  renderKeyboard($("#detected-keyboard"), new Set(midiNotes), state.detectedVelocity);
  $("#detected-notes").textContent = midiNotes.length ? midiNotes.map((midi) => midiNameWithoutOctave(midi)).join(" · ") : "Play a chord to begin";
  const chord = identifyChord(midiNotes);
  if (!chord) {
    $("#detected-name").textContent = midiNotes.length ? "Keep playing…" : "—";
    $("#detected-meta").textContent = midiNotes.length ? "Add a few notes for a chord" : "Waiting for a chord";
    renderSuggestions(null);
    return;
  }
  const newName = chordName(chord.root, chord.quality);
  if ($("#detected-name").textContent !== newName) {
    $("#detected-name").textContent = newName;
    $("#detected-name").classList.remove("pop-animation");
    void $("#detected-name").offsetWidth;
    $("#detected-name").classList.add("pop-animation");
  }
  $("#detected-meta").textContent = `${CHORDS[chord.quality].label.toLowerCase()} chord`;
  renderSuggestions(chord);
}

function midiNameWithoutOctave(midi) {
  return noteName(midi % 12);
}

function renderSuggestions(chord) {
  const container = $("#suggestion-list");
  container.replaceChildren();
  if (!chord) {
    const empty = document.createElement("div");
    empty.className = "empty-suggestions";
    empty.textContent = "Your chord ideas will show up here as you play.";
    container.append(empty);
    return;
  }
  getEnhancements(chord, $("#mood-select").value, state.detectedVelocity, state.playStyle).forEach((suggestion) => {
    const card = document.createElement("article");
    card.className = "suggestion-card";
    const top = document.createElement("div");
    top.className = "suggestion-top";
    const name = document.createElement("span");
    name.className = "suggestion-name";
    name.textContent = suggestion.name;
    const tag = document.createElement("span");
    tag.className = "suggestion-tag";
    tag.textContent = suggestion.tag;
    top.append(name, tag);
    const copy = document.createElement("p");
    copy.textContent = suggestion.copy;
    const footer = document.createElement("div");
    footer.className = "suggestion-footer";
    const notes = document.createElement("span");
    notes.className = "suggestion-notes";
    notes.textContent = suggestion.notes.map((midi) => noteName(midi % 12)).join(" · ");
    const play = document.createElement("button");
    play.className = "suggestion-play";
    play.setAttribute("aria-label", `Play ${suggestion.name}`);
    play.innerHTML = '<span class="play-triangle" aria-hidden="true"></span>';
    play.addEventListener("click", () => playNotes(suggestion.notes));
    footer.append(notes, play);
    card.append(top, copy, footer);
    
    card.draggable = true;
    card.title = "Drag this chord to your DAW to export MIDI";
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("DownloadURL", makeMidiDragData([suggestion.notes], `${suggestion.name}.mid`));
      e.dataTransfer.effectAllowed = "copy";
    });
    
    container.append(card);
  });
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 3000);
}

function setStatus(message, kind = "") {
  const status = $("#listen-status");
  status.classList.toggle("listening", kind === "listening");
  status.classList.toggle("error", kind === "error");
  $("#status-message").textContent = message;
  $("#stop-listening").hidden = kind !== "listening";
}

function midiFrequencyToNote(frequency) {
  return 69 + 12 * Math.log2(frequency / 440);
}

function detectMicNotes(analyser, sampleRate) {
  const spectrum = new Float32Array(analyser.frequencyBinCount);
  analyser.getFloatFrequencyData(spectrum);
  const binHz = sampleRate / analyser.fftSize;
  const energies = [];
  const readBand = (frequency, width = 2) => {
    const center = Math.round(frequency / binHz);
    let total = 0;
    for (let offset = -width; offset <= width; offset += 1) {
      const value = spectrum[center + offset] ?? -120;
      total += 10 ** (Math.max(-90, value) / 10);
    }
    return total;
  };
  for (let midi = 36; midi <= 88; midi += 1) {
    const fundamental = 440 * (2 ** ((midi - 69) / 12));
    let score = 0;
    [1, 2, 3, 4, 5].forEach((harmonic, index) => {
      if (fundamental * harmonic < sampleRate / 2) score += readBand(fundamental * harmonic, index === 0 ? 2 : 1) / (harmonic ** 0.72);
    });
    const competingOctave = midi + 12 <= 88 ? energies[midi - 35] : 0;
    energies.push({ midi, score: competingOctave ? score - competingOctave * 0.25 : score });
  }
  const peak = Math.max(...energies.map(({ score }) => score), 0.000001);
  const notes = energies
    .filter(({ score }) => score > peak * 0.17)
    .sort((left, right) => right.score - left.score)
    .slice(0, 8)
    .map(({ midi }) => midi);
  return { notes, peak };
}

async function startMic() {
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus("Microphone access needs a modern browser on localhost or HTTPS.", "error");
    return;
  }
  stopListening();
  $("#mic-button").disabled = true;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) throw new Error("Web Audio is not supported in this browser.");
    state.stream = stream;
    const context = state.audioContext || new AudioContextClass();
    state.audioContext = context;
    await context.resume();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    analyser.fftSize = 8192;
    analyser.smoothingTimeConstant = 0.72;
    source.connect(analyser);
    state.micActive = true;
    $("#mic-button").disabled = false;
    setStatus("Listening — play a clear chord near your microphone.", "listening");
    const processFrame = () => {
      if (!state.micActive) return;
      const { notes, peak } = detectMicNotes(analyser, context.sampleRate);
      if (notes.length >= 3) {
          if (state.detectedMidi.size === 0 || notes.some(n => !state.detectedMidi.has(n))) {
              const now = performance.now();
              if (now - state.lastNoteTime > 80 && now - state.lastNoteTime < 800) {
                  state.playStyle = "arpeggio";
              } else if (state.detectedMidi.size === 0) {
                  state.playStyle = "block";
              }
              state.lastNoteTime = now;
          }
          state.detectedMidi = new Set(notes);
          state.detectedVelocity = Math.min(1, peak / 30);
      } else if (notes.length === 0 && state.detectedMidi.size) {
          state.detectedMidi.clear();
      }
      updateDetected();
      state.animationFrame = requestAnimationFrame(processFrame);
    };
    processFrame();
  } catch (error) {
    $("#mic-button").disabled = false;
    setStatus(error.name === "NotAllowedError" ? "Microphone permission was denied. Allow it in your browser settings and try again." : `Could not start microphone: ${error.message}`, "error");
  }
}

function noteOn(note, velocity) {
  const now = performance.now();
  if (state.detectedMidi.size === 0) {
    state.lastNoteTime = now;
    state.playStyle = "block";
  } else {
    const gap = now - state.lastNoteTime;
    if (gap > 80 && gap < 800) {
      state.playStyle = "arpeggio";
    }
  }
  state.lastNoteTime = now;
  state.detectedMidi.add(note);
  state.detectedVelocity = velocity / 127;
  updateDetected();
}

function noteOff(note) {
  state.detectedMidi.delete(note);
  updateDetected();
}

async function connectMidi() {
  if (!navigator.requestMIDIAccess) {
    setStatus("Web MIDI isn’t available here. Try Chrome or Edge on desktop.", "error");
    return;
  }
  stopListening();
  try {
    const access = await navigator.requestMIDIAccess();
    state.midiAccess = access;
    state.midiInputs = [...access.inputs.values()];
    if (!state.midiInputs.length) {
      setStatus("MIDI is ready, but no keyboard is connected. Plug one in and try again.", "error");
      return;
    }
    state.midiInputs.forEach((input) => {
      input.onmidimessage = (event) => {
        const [command, note, velocity] = event.data;
        if (command >= 144 && command < 160 && velocity > 0) noteOn(note, velocity);
        else if ((command >= 128 && command < 144) || (command >= 144 && command < 160 && velocity === 0)) noteOff(note);
      };
    });
    access.onstatechange = () => {
      state.midiInputs = [...access.inputs.values()];
      if (!state.midiInputs.length) {
        state.detectedMidi.clear();
        updateDetected();
        setStatus("MIDI keyboard disconnected.", "");
      }
    };
    setStatus(`Connected to ${state.midiInputs.length === 1 ? state.midiInputs[0].name || "MIDI keyboard" : `${state.midiInputs.length} MIDI devices`}. Play a chord.`, "listening");
  } catch (error) {
    setStatus(error.name === "SecurityError" ? "MIDI access requires a secure browser context." : `Could not connect to MIDI: ${error.message}`, "error");
  }
}

function stopListening() {
  state.micActive = false;
  if (state.animationFrame) cancelAnimationFrame(state.animationFrame);
  state.animationFrame = null;
  if (state.stream) state.stream.getTracks().forEach((track) => track.stop());
  state.stream = null;
  state.midiInputs.forEach((input) => { input.onmidimessage = null; });
  state.midiInputs = [];
  state.detectedMidi.clear();
  updateDetected();
  $("#mic-button").disabled = false;
  setStatus("Choose an input to start listening.");
}

const SCALE = [0, 2, 4, 5, 7, 9, 11];
function scaleChord(root, degree, quality) {
  const rootPc = (root + SCALE[degree % 7]) % 12;
  return { root: rootPc, quality, notes: makeVoicing(rootPc, quality, 0, 3) };
}

function makeProgression() {
  const definitions = {
    pop: [[0, "maj"], [4, "maj"], [5, "min"], [3, "maj"]],
    warm: [[5, "min"], [3, "maj"], [0, "maj"], [4, "maj"]],
    jazz: [[1, "min7"], [4, "7"], [0, "maj7"], [5, "min7"]],
    dreamy: [[0, "maj7"], [2, "min7"], [3, "maj7"], [3, "min"]],
    neosoul: [[1, "min9"], [4, "7b9"], [0, "maj9"], [5, "min9"]],
    lofi: [[1, "min9"], [4, "min9"], [0, "maj9"], [5, "7b9"]],
    bossa: [[0, "maj9"], [0, "dim"], [1, "min9"], [4, "7b9"]],
    jpop: [[3, "maj7"], [4, "7"], [2, "min7"], [5, "min7"]],
    gospel: [[0, "maj"], [0, "7"], [3, "maj7"], [3, "min6"]],
  };
  const progression = definitions[$("#progression-select").value].map(([degree, quality]) => scaleChord(selectedRoot(), degree, quality));
  state.progression = progression;
  const target = $("#progression-result");
  target.replaceChildren();
  progression.forEach((chord) => {
    const button = document.createElement("button");
    button.className = "progression-chord";
    const name = document.createElement("b");
    name.textContent = chordName(chord.root, chord.quality);
    const detail = document.createElement("small");
    detail.textContent = CHORDS[chord.quality].label.toLowerCase();
    button.append(name, detail);
    button.addEventListener("click", () => playNotes(chord.notes));
    target.append(button);
  });
  target.hidden = false;
}

function changeTab(tab) {
  const isGenerator = tab === "generator";
  $("#generator-tab").classList.toggle("active", isGenerator);
  $("#listener-tab").classList.toggle("active", !isGenerator);
  $("#generator-tab").setAttribute("aria-selected", String(isGenerator));
  $("#listener-tab").setAttribute("aria-selected", String(!isGenerator));
  $("#generator-panel").hidden = !isGenerator;
  $("#listener-panel").hidden = isGenerator;
}

$("#generate-button").addEventListener("click", updateGeneratedChord);
["root-select", "quality-select", "inversion-select", "voicing-select"].forEach((id) => $(`#${id}`).addEventListener("change", updateGeneratedChord));
$("#play-generated").addEventListener("click", () => state.generated && playNotes(state.generated.notes));
$("#export-generated").addEventListener("click", () => state.generated && downloadMidi([state.generated.notes], `${chordName(state.generated.root, state.generated.quality)}.mid`));
$("#progression-button").addEventListener("click", makeProgression);
$("#export-progression").addEventListener("click", () => downloadMidi((state.progression || []).map((chord) => chord.notes), "chordcraft-progression.mid"));
$("#generator-tab").addEventListener("click", () => changeTab("generator"));
$("#listener-tab").addEventListener("click", () => changeTab("listener"));
$("#mic-button").addEventListener("click", startMic);
$("#midi-button").addEventListener("click", connectMidi);
$("#stop-listening").addEventListener("click", stopListening);
$("#mood-select").addEventListener("change", updateDetected);
$("#help-button").addEventListener("click", () => $("#help-dialog").showModal());
$("#close-help").addEventListener("click", () => $("#help-dialog").close());

setupMidiDraggable("export-generated", () => state.generated ? [state.generated.notes] : [], () => `${chordName(state.generated.root, state.generated.quality)}.mid`);
setupMidiDraggable("export-progression", () => (state.progression || []).map((chord) => chord.notes), () => "chordcraft-progression.mid");

updateGeneratedChord();
updateDetected();
