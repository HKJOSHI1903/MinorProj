// Hindi / English text for the whole interface.
// Components call t('some.key'); the chosen language is remembered in the browser.
// Disease names and treatment advice come from the server in English.

import { ref } from 'vue'

const messages = {
  en: {
    brand: 'Kisan Sahayak',
    nav: { features: 'Features', how: 'How it works', crops: 'Crops', model: 'The model', open: 'Open app' },
    hero: {
      eyebrow: 'AI crop care for Indian farmers',
      title1: 'Spot crop disease',
      title2: 'before it spreads.',
      text: 'Photograph one leaf. Kisan Sahayak names the disease and tells you how to treat it, in Hindi or English.',
      primary: 'Scan a leaf',
      secondary: 'See how it works',
      chipScan: 'Scanning leaf',
      chipSpot: 'Infected area found',
      chipPlan: 'Treatment plan ready',
    },
    stats: { accuracy: 'accuracy on unseen test photos', conditions: 'leaf conditions recognised', crops: 'crops covered', photos: 'photos used for training' },
    features: {
      kicker: 'What it does',
      title: 'One assistant for the whole season',
      live: 'Live',
      soon: 'In development',
      disease: { title: 'Disease detection', text: 'A neural network trained on thousands of leaf photos recognises the disease and how sure it is.' },
      advice: { title: 'Organic and chemical options', text: 'Every diagnosis comes with organic steps, chemical options and ways to prevent it next season.' },
      safety: { title: 'Honest about doubt', text: 'Below 70% confidence the app says so and points you to your Krishi Vigyan Kendra instead of guessing.' },
      language: { title: 'Hindi and English', text: 'Switch language with one tap. Large text and buttons made for the field.' },
      crop: { title: 'Crop advisor', text: 'Enter soil nutrients, pH, rainfall and temperature to get the crop that fits your land.' },
      assistant: { title: 'Farming assistant', text: 'Ask questions in your own words and get answers drawn from agriculture advisories.' },
    },
    how: {
      kicker: 'How it works',
      title: 'From photo to treatment in three steps',
      s1: { title: 'Take a photo', text: 'One leaf, plain background, daylight. Use your phone camera or upload a picture.' },
      s2: { title: 'AI checks the leaf', text: 'The model compares it with the patterns of 38 leaf conditions and reports its confidence.' },
      s3: { title: 'Get the treatment', text: 'See symptoms, cause, organic and chemical options, and how to prevent it.' },
    },
    crops: { kicker: 'Coverage', title: 'Crops it knows today' },
    model: {
      kicker: 'Under the hood',
      title: 'Built on measured results',
      text: 'The numbers below come straight from the last training run. The test photos were never shown to the model during training.',
      arch: 'Architecture',
      archValue: 'MobileNetV2, transfer learning',
      data: 'Dataset',
      dataValue: 'PlantVillage leaf images',
      split: 'Evaluation',
      splitValue: '70% train, 15% validation, 15% test',
      threshold: 'Confidence threshold',
      thresholdValue: 'Results under 70% are flagged',
      precision: 'Macro precision',
      recall: 'Macro recall',
      f1: 'Macro F1-score',
      accuracy: 'Test accuracy',
      offline: 'Start the server to see live model results.',
    },
    cta: { title: 'Your crop cannot wait.', text: 'Check a leaf now. It takes a few seconds.', button: 'Open Kisan Sahayak' },
    footer: { note: 'General advice only. Confirm with your local Krishi Vigyan Kendra or agriculture officer before treating the crop.' },
    app: {
      overview: 'Overview',
      disease: 'Disease scan',
      crop: 'Crop advisor',
      assistant: 'Assistant',
      soon: 'Soon',
      site: 'Back to website',
      online: 'Model online',
      offline: 'Server offline',
      checking: 'Connecting',
    },
    overview: {
      morning: 'Good morning',
      afternoon: 'Good afternoon',
      evening: 'Good evening',
      subtitle: 'What would you like to check today?',
      scanTitle: 'Scan a leaf',
      scanText: 'Find out what is wrong with your crop and how to treat it.',
      scanButton: 'Start a scan',
      scans: 'Scans',
      healthy: 'Healthy',
      diseased: 'Diseased',
      unsure: 'Unsure',
      recent: 'Recent scans',
      clear: 'Clear',
      empty: 'No scans yet',
      emptyText: 'Your scans will appear here. They stay on this device.',
      modules: 'Modules',
      accuracy: 'Model accuracy',
      accuracyNote: 'on unseen test photos',
    },
    scan: {
      title: 'Disease scan',
      subtitle: 'Upload or take a photo of one leaf.',
      drop: 'Drop a leaf photo here',
      or: 'or',
      choose: 'Choose photo',
      camera: 'Use camera',
      formats: 'JPG, PNG or WEBP, up to 10 MB',
      tipsTitle: 'For the best result',
      tip1: 'One leaf in the frame',
      tip2: 'Plain background',
      tip3: 'Daylight, no flash',
      analysing: 'Checking the leaf',
      again: 'Scan another leaf',
      crop: 'Crop',
      result: 'Result',
      confidence: 'confidence',
      healthyLeaf: 'Healthy leaf',
      lowTitle: 'The model is not sure',
      lowText: 'Confidence is below {threshold}%. Do not rely on this result. Take a clearer photo and consult your local Krishi Vigyan Kendra (KVK) or agriculture officer before treating the crop.',
      symptoms: 'Symptoms',
      cause: 'Cause',
      organic: 'Organic',
      chemical: 'Chemical',
      prevention: 'Prevention',
      care: 'Keep it healthy',
      others: 'Other possibilities',
      noAdvice: 'No advice is stored for this condition yet.',
      disclaimer: 'General advice only. Read the product label and confirm with your local KVK or agriculture officer before treating the crop.',
      capture: 'Take photo',
      cancel: 'Cancel',
      cameraError: 'The camera could not be opened. Allow camera access or upload a photo instead.',
      waiting: 'Your result will appear here',
      waitingText: 'Add a leaf photo to start.',
    },
    errors: {
      invalid_image: 'This file is not a photo. Please use a JPG or PNG image.',
      image_too_small: 'This photo is too small. Please take a closer, clearer photo.',
      file_too_large: 'This photo is larger than 10 MB. Please choose a smaller one.',
      no_file: 'No photo was selected.',
      model_missing: 'The model has not been trained yet.',
      offline: 'The server cannot be reached. Start it with "python -m api.server" and try again.',
      server_error: 'Something went wrong on the server. Please try again.',
      not_image_type: 'Please choose an image file (JPG, PNG or WEBP).',
    },
    soon: {
      badge: 'In development',
      crop: {
        title: 'Crop advisor',
        text: 'Tell it your soil nitrogen, phosphorus, potassium, pH, temperature, humidity and rainfall, and it will recommend the crop that suits your field.',
        p1: 'Trained on the Crop Recommendation dataset (22 crops)',
        p2: 'Compares Random Forest, Decision Tree, SVM and XGBoost',
        p3: 'Explains why a crop was chosen',
      },
      assistant: {
        title: 'Farming assistant',
        text: 'Ask a question in Hindi or English and get an answer drawn from agriculture advisories. It will also explain your scan results in simple words.',
        p1: 'Answers only from trusted documents',
        p2: 'Understands your latest scan result',
        p3: 'Hindi and English',
      },
      back: 'Scan a leaf meanwhile',
    },
    time: { now: 'just now', min: '{n} min ago', hour: '{n} h ago', day: '{n} d ago' },
  },

  hi: {
    brand: 'किसान सहायक',
    nav: { features: 'खूबियाँ', how: 'कैसे काम करता है', crops: 'फसलें', model: 'मॉडल', open: 'ऐप खोलें' },
    hero: {
      eyebrow: 'भारतीय किसानों के लिए AI फसल देखभाल',
      title1: 'फसल का रोग पहचानें,',
      title2: 'फैलने से पहले।',
      text: 'एक पत्ती की फोटो लें। किसान सहायक रोग का नाम और उसका इलाज बताता है, हिन्दी या अंग्रेज़ी में।',
      primary: 'पत्ती जाँचें',
      secondary: 'देखें कैसे काम करता है',
      chipScan: 'पत्ती की जाँच जारी',
      chipSpot: 'संक्रमित हिस्सा मिला',
      chipPlan: 'इलाज की योजना तैयार',
    },
    stats: { accuracy: 'नई टेस्ट फोटो पर सटीकता', conditions: 'पत्ती की स्थितियाँ पहचानता है', crops: 'फसलें शामिल', photos: 'ट्रेनिंग में इस्तेमाल फोटो' },
    features: {
      kicker: 'यह क्या करता है',
      title: 'पूरे मौसम के लिए एक सहायक',
      live: 'चालू',
      soon: 'बन रहा है',
      disease: { title: 'रोग की पहचान', text: 'हज़ारों पत्तियों की फोटो पर सीखा न्यूरल नेटवर्क रोग पहचानता है और बताता है कि उसे कितना भरोसा है।' },
      advice: { title: 'जैविक और रासायनिक उपाय', text: 'हर नतीजे के साथ जैविक उपाय, रासायनिक विकल्प और अगले मौसम के लिए बचाव के तरीके।' },
      safety: { title: 'शक हो तो साफ़ बताता है', text: '70% से कम भरोसे पर ऐप अंदाज़ा नहीं लगाता, बल्कि आपको कृषि विज्ञान केंद्र से सलाह लेने को कहता है।' },
      language: { title: 'हिन्दी और अंग्रेज़ी', text: 'एक टैप में भाषा बदलें। बड़े अक्षर और बटन, खेत में इस्तेमाल के लिए।' },
      crop: { title: 'फसल सलाहकार', text: 'मिट्टी के पोषक तत्व, pH, बारिश और तापमान डालें और अपनी ज़मीन के लिए सही फसल जानें।' },
      assistant: { title: 'खेती सहायक', text: 'अपने शब्दों में सवाल पूछें और कृषि सलाह के दस्तावेज़ों से जवाब पाएँ।' },
    },
    how: {
      kicker: 'कैसे काम करता है',
      title: 'फोटो से इलाज तक, तीन कदम में',
      s1: { title: 'फोटो लें', text: 'एक पत्ती, सादा बैकग्राउंड, दिन की रोशनी। फोन के कैमरे से लें या फोटो अपलोड करें।' },
      s2: { title: 'AI पत्ती जाँचता है', text: 'मॉडल इसे 38 स्थितियों के पैटर्न से मिलाता है और अपना भरोसा बताता है।' },
      s3: { title: 'इलाज जानें', text: 'लक्षण, कारण, जैविक और रासायनिक उपाय और बचाव के तरीके देखें।' },
    },
    crops: { kicker: 'दायरा', title: 'आज यह इन फसलों को जानता है' },
    model: {
      kicker: 'अंदर की बात',
      title: 'नापे हुए नतीजों पर बना',
      text: 'नीचे के आँकड़े सीधे पिछली ट्रेनिंग से लिए गए हैं। टेस्ट की फोटो ट्रेनिंग के दौरान मॉडल को कभी नहीं दिखाई गईं।',
      arch: 'आर्किटेक्चर',
      archValue: 'MobileNetV2, ट्रांसफर लर्निंग',
      data: 'डेटासेट',
      dataValue: 'PlantVillage पत्ती की फोटो',
      split: 'मूल्यांकन',
      splitValue: '70% ट्रेन, 15% वैलिडेशन, 15% टेस्ट',
      threshold: 'भरोसे की सीमा',
      thresholdValue: '70% से कम नतीजों पर चेतावनी',
      precision: 'मैक्रो प्रिसिज़न',
      recall: 'मैक्रो रिकॉल',
      f1: 'मैक्रो F1-स्कोर',
      accuracy: 'टेस्ट सटीकता',
      offline: 'मॉडल के असली नतीजे देखने के लिए सर्वर चालू करें।',
    },
    cta: { title: 'आपकी फसल इंतज़ार नहीं कर सकती।', text: 'अभी एक पत्ती जाँचें। कुछ ही सेकंड लगते हैं।', button: 'किसान सहायक खोलें' },
    footer: { note: 'यह केवल सामान्य सलाह है। इलाज से पहले अपने नज़दीकी कृषि विज्ञान केंद्र या कृषि अधिकारी से पुष्टि करें।' },
    app: {
      overview: 'होम',
      disease: 'रोग की जाँच',
      crop: 'फसल सलाहकार',
      assistant: 'सहायक',
      soon: 'जल्द',
      site: 'वेबसाइट पर वापस',
      online: 'मॉडल चालू है',
      offline: 'सर्वर बंद है',
      checking: 'जुड़ रहा है',
    },
    overview: {
      morning: 'सुप्रभात',
      afternoon: 'नमस्ते',
      evening: 'शुभ संध्या',
      subtitle: 'आज आप क्या जाँचना चाहेंगे?',
      scanTitle: 'पत्ती जाँचें',
      scanText: 'जानें आपकी फसल को क्या हुआ है और उसका इलाज क्या है।',
      scanButton: 'जाँच शुरू करें',
      scans: 'जाँचें',
      healthy: 'स्वस्थ',
      diseased: 'रोगी',
      unsure: 'अनिश्चित',
      recent: 'हाल की जाँचें',
      clear: 'हटाएँ',
      empty: 'अभी कोई जाँच नहीं',
      emptyText: 'आपकी जाँचें यहाँ दिखेंगी। ये इसी डिवाइस पर रहती हैं।',
      modules: 'मॉड्यूल',
      accuracy: 'मॉडल की सटीकता',
      accuracyNote: 'नई टेस्ट फोटो पर',
    },
    scan: {
      title: 'रोग की जाँच',
      subtitle: 'एक पत्ती की फोटो अपलोड करें या खींचें।',
      drop: 'पत्ती की फोटो यहाँ छोड़ें',
      or: 'या',
      choose: 'फोटो चुनें',
      camera: 'कैमरा चलाएँ',
      formats: 'JPG, PNG या WEBP, 10 MB तक',
      tipsTitle: 'अच्छे नतीजे के लिए',
      tip1: 'फ्रेम में एक ही पत्ती',
      tip2: 'सादा बैकग्राउंड',
      tip3: 'दिन की रोशनी, फ्लैश नहीं',
      analysing: 'पत्ती की जाँच हो रही है',
      again: 'दूसरी पत्ती जाँचें',
      crop: 'फसल',
      result: 'नतीजा',
      confidence: 'भरोसा',
      healthyLeaf: 'स्वस्थ पत्ती',
      lowTitle: 'मॉडल को पूरा भरोसा नहीं है',
      lowText: 'भरोसा {threshold}% से कम है। इस नतीजे पर निर्भर न रहें। साफ़ फोटो दोबारा लें और इलाज से पहले अपने नज़दीकी कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से सलाह लें।',
      symptoms: 'लक्षण',
      cause: 'कारण',
      organic: 'जैविक',
      chemical: 'रासायनिक',
      prevention: 'बचाव',
      care: 'स्वस्थ रखें',
      others: 'अन्य संभावनाएँ',
      noAdvice: 'इस स्थिति के लिए अभी सलाह उपलब्ध नहीं है।',
      disclaimer: 'यह केवल सामान्य सलाह है। दवा का लेबल पढ़ें और इलाज से पहले अपने नज़दीकी KVK या कृषि अधिकारी से पुष्टि करें। इलाज की सलाह अभी अंग्रेज़ी में है।',
      capture: 'फोटो खींचें',
      cancel: 'रद्द करें',
      cameraError: 'कैमरा नहीं खुल सका। कैमरे की अनुमति दें या फोटो अपलोड करें।',
      waiting: 'आपका नतीजा यहाँ दिखेगा',
      waitingText: 'शुरू करने के लिए पत्ती की फोटो डालें।',
    },
    errors: {
      invalid_image: 'यह फ़ाइल फोटो नहीं है। कृपया JPG या PNG फोटो डालें।',
      image_too_small: 'यह फोटो बहुत छोटी है। कृपया पास से साफ़ फोटो लें।',
      file_too_large: 'यह फोटो 10 MB से बड़ी है। कृपया छोटी फोटो चुनें।',
      no_file: 'कोई फोटो नहीं चुनी गई।',
      model_missing: 'मॉडल अभी ट्रेन नहीं हुआ है।',
      offline: 'सर्वर से संपर्क नहीं हो पा रहा। "python -m api.server" से चालू करें और दोबारा कोशिश करें।',
      server_error: 'सर्वर में कुछ गड़बड़ हुई। कृपया दोबारा कोशिश करें।',
      not_image_type: 'कृपया फोटो फ़ाइल चुनें (JPG, PNG या WEBP)।',
    },
    soon: {
      badge: 'बन रहा है',
      crop: {
        title: 'फसल सलाहकार',
        text: 'मिट्टी का नाइट्रोजन, फॉस्फोरस, पोटाश, pH, तापमान, नमी और बारिश बताएँ, और यह आपके खेत के लिए सही फसल सुझाएगा।',
        p1: 'Crop Recommendation डेटासेट (22 फसलें) पर ट्रेन',
        p2: 'Random Forest, Decision Tree, SVM और XGBoost की तुलना',
        p3: 'बताता है कि फसल क्यों चुनी गई',
      },
      assistant: {
        title: 'खेती सहायक',
        text: 'हिन्दी या अंग्रेज़ी में सवाल पूछें और कृषि सलाह के दस्तावेज़ों से जवाब पाएँ। यह आपकी जाँच के नतीजे भी सरल शब्दों में समझाएगा।',
        p1: 'केवल भरोसेमंद दस्तावेज़ों से जवाब',
        p2: 'आपकी पिछली जाँच का नतीजा समझता है',
        p3: 'हिन्दी और अंग्रेज़ी',
      },
      back: 'तब तक एक पत्ती जाँचें',
    },
    time: { now: 'अभी', min: '{n} मिनट पहले', hour: '{n} घंटे पहले', day: '{n} दिन पहले' },
  },
}

// Hindi names for the 14 crops the model knows.
const CROPS_HI = {
  Apple: 'सेब',
  Blueberry: 'ब्लूबेरी',
  'Cherry (including sour)': 'चेरी',
  'Corn (maize)': 'मक्का',
  Grape: 'अंगूर',
  Orange: 'संतरा',
  Peach: 'आड़ू',
  'Pepper, bell': 'शिमला मिर्च',
  Potato: 'आलू',
  Raspberry: 'रसभरी',
  Soybean: 'सोयाबीन',
  Squash: 'कद्दू',
  Strawberry: 'स्ट्रॉबेरी',
  Tomato: 'टमाटर',
}

const STORAGE_KEY = 'kisan.lang'

function savedLanguage() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'hi' ? 'hi' : 'en'
  } catch {
    return 'en'
  }
}

const lang = ref(savedLanguage())

function setLanguage(code) {
  lang.value = code === 'hi' ? 'hi' : 'en'
  try {
    localStorage.setItem(STORAGE_KEY, lang.value)
  } catch {
    // private browsing: the choice just lasts for this visit
  }
}

// t('scan.lowText', { threshold: 70 }) -> the text in the current language.
function t(key, values) {
  let text = key.split('.').reduce((node, part) => node?.[part], messages[lang.value])
  if (typeof text !== 'string') return key
  if (values) for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value)
  return text
}

// 'Tomato' -> 'टमाटर' in Hindi (with the English name alongside when `both` is true).
function cropName(crop, both = false) {
  if (lang.value === 'hi' && CROPS_HI[crop]) return both ? `${CROPS_HI[crop]} (${crop})` : CROPS_HI[crop]
  return crop
}

export function useI18n() {
  return { lang, setLanguage, t, cropName }
}
