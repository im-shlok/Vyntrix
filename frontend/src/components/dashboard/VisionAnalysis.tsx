'use client';

import React, { useState } from 'react';
import { Camera, Upload, AlertTriangle, ShieldCheck, HeartPulse, Sparkles, Cpu, Layers, RefreshCw } from 'lucide-react';

interface VisionAnalysisProps {
  onAnalyzeComplete: (data: any) => void;
  activeLanguage: string;
}

export default function VisionAnalysis({ onAnalyzeComplete, activeLanguage }: VisionAnalysisProps) {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const labels: any = {
    en: {
      title: "Leaf & Crop AI Analyzer",
      description: "YOLOv8s Leaf Detection",
      dragText: "Drop leaf image or click to browse",
      analyzing: "Scanning plant tissues...",
      confidence: "Confidence Score",
      severity: "Severity Level",
      remedy: "Immediate Action Suggested",
      uploadNew: "Upload Another Photo",
      hudTitle: "VISION_INTELLIGENCE_HUD"
    },
    hi: {
      title: "पत्ता और एआई विश्लेषक",
      description: "YOLOv11 और SAM2 पादप ऊतक निदान",
      dragText: "पत्ते की छवि खींचें या फ़ाइल चुनें",
      analyzing: "ऊतकों का विश्लेषण हो रहा है...",
      confidence: "विश्वास स्कोर",
      severity: "तीव्रता स्तर",
      remedy: "सुझाई गई तत्काल कार्रवाई",
      uploadNew: "दूसरा फोटो अपलोड करें",
      hudTitle: "दृष्टि_आसूचना_एचयूडी"
    },
    pa: {
      title: "ਪੱਤਾ ਅਤੇ ਫਸਲ ਏਆਈ ਵਿਸ਼ਲੇਸ਼ਕ",
      description: "YOLOv11 ਅਤੇ SAM2 ਪੌਦੇ ਦੇ ਟਿਸ਼ੂ ਨਿਦਾਨ",
      dragText: "ਪੱਤੇ ਦੀ ਫੋਟੋ ਖਿੱਚੋ ਜਾਂ ਫਾਈਲ ਚੁਣੋ",
      analyzing: "ਪੌਦੇ ਦੇ ਟਿਸ਼ੂਆਂ ਦੀ ਸਕੈਨਿੰਗ ਜਾਰੀ...",
      confidence: "ਭਰੋਸੇਯੋਗਤਾ ਸਕੋਰ",
      severity: "ਗੰਭੀਰਤਾ ਦਾ ਪੱਧਰ",
      remedy: "ਤੁਰੰਤ ਸੁਝਾਈ ਗਈ ਕਾਰਵਾਈ",
      uploadNew: "ਹੋਰ ਫੋਟੋ ਅਪਲੋਡ ਕਰੋ",
      hudTitle: "ਦ੍ਰਿਸ਼ਟੀ_ਸਕੈਨਰ_ਐਚਯੂਡੀ"
    },
    mr: {
      title: "पाने आणि पीक एआय विश्लेषक",
      description: "YOLOv11 आणि SAM2 वनस्पती ऊती निदान",
      dragText: "पानाचे चित्र येथे ओढा किंवा फाइल निवडा",
      analyzing: "वनस्पती पेशींचे स्कॅनिंग सुरू आहे...",
      confidence: "विश्वासार्हता स्कोअर",
      severity: "तीव्रता पातळी",
      remedy: "त्वरित सुचवलेली कारवाई",
      uploadNew: "दुसरा फोटो अपलोड करा",
      hudTitle: "दृष्टी_माहिती_एचयूडी"
    },
    te: {
      title: "ఆకు & పంట ఎఐ విశ్లేషణ",
      description: "YOLOv11 & SAM2 ప్లాంట్ టిష్యూ డయాగ్నస్టిక్",
      dragText: "ఆకు చిత్రాన్ని లాగి ఇక్కడ వదలండి లేదా ఎంచుకోండి",
      analyzing: "మొక్క కణజాలాలను స్కాన్ చేస్తున్నాము...",
      confidence: "ವಿಶ್ವಸనీయత స్కోరు",
      severity: "తీव्रత స్థాయి",
      remedy: "తక్షణమే సూచించబడిన చర్య",
      uploadNew: "మరో ఫోటో అప్‌లోడ్ చేయండి",
      hudTitle: "విజన్_ఇంటెలిజెన్స్_హెచ్‌ಯುడి"
    },
    ta: {
      title: "இலை மற்றும் பயிர் AI பகுப்பாய்வி",
      description: "YOLOv11 & SAM2 தாவர திசு கண்டறிதல்",
      dragText: "இலை படத்தை இழுத்து இங்கு விடவும் அல்லது தேடவும்",
      analyzing: "தாவர திசுக்களை ஸ்கேன் செய்கிறது...",
      confidence: "நம்பிக்கை மதிப்பெண்",
      severity: "தீவிரத்தன்மை நிலை",
      remedy: "பரிந்துரைக்கப்படும் உடனடி நடவடிக்கை",
      uploadNew: "மற்றொரு புகைப்படத்தைப் பதிவேற்றவும்",
      hudTitle: "பார்வை_நுண்ணறிவு_ஹச்யுடி"
    },
    kn: {
      title: "ಎಲೆ ಮತ್ತು ಬೆಳೆ ಎಐ ವಿಶ್ಲೇಷಕ",
      description: "YOLOv11 & SAM2 ಸಸ್ಯ ಅಂಗಾಂಶ ರೋಗನಿರ್ಣಯ",
      dragText: "ಎಲೆಯ ಚಿತ್ರವನ್ನು ಇಲ್ಲಿಗೆ ಎಳೆಯಿರಿ ಅಥವಾ ಆರಿಸಿ",
      analyzing: "ಸಸ್ಯದ ಅಂಗಾಂಶಗಳನ್ನು ಸ್ಕ್ಯಾನ್ ಮಾಡಲಾಗುತ್ತಿದೆ...",
      confidence: "ವಿಶ್ವಾಸಾರ್ಹತೆ ಸ್ಕೋರ್",
      severity: "ತೀವ್ರತೆಯ ಮಟ್ಟ",
      remedy: "ತಕ್ಷಣ ಸೂಚಿಸಲಾದ ಕ್ರಮ",
      uploadNew: "ಮತ್ತೊಂದು ಫೋಟೋ ಅಪ್ಲೋಡ್ ಮಾಡಿ",
      hudTitle: "ವಿಷನ್_ಇಂಟೆಲಿಜೆನ್ಸ್_ಎಚ್‌ಯುಡಿ"
    },
    gu: {
      title: "પર્ણ અને પાક એઆઈ વિશ્લેષક",
      description: "પર્ણ અને પાક એઆઈ વિશ્લેષક",
      dragText: "પાંદડાની છબી ખેંચીને અહીં લાવો અથવા ફાઈલ શોધો",
      analyzing: "વનસ્પતિ પેશીઓનું સ્કેનિંગ ચાલુ...",
      confidence: "વિશ્વાસ સ્કોર",
      severity: "તીવ્રતાનું સ્તર",
      remedy: "તાત્કાલિક ભલામણ કરેલ પગલાં",
      uploadNew: "બીજો ફોટો અપલોડ કરો",
      hudTitle: "વિઝન_ઇન્ટેલિજન્સ_એચયુડી"
    },
    bn: {
      title: "পাতা ও ফসল এআই বিশ্লেষক",
      description: "YOLOv11 ও SAM2 উদ্ভিদ টিস্যু নির্ণয়",
      dragText: "পাতাটি টেনে এনে এখানে রাখুন বা ফাইল সিলেক্ট করুন",
      analyzing: "উদ্ভিদ টিস্যু স্ক্যান করা হচ্ছে...",
      confidence: "নির্ভরযোগ্যতার স্কোর",
      severity: "আক্রান্তের মাত্রা",
      remedy: "তাত্ক্ষণিক প্রস্তাবিত পদক্ষেপ",
      uploadNew: "অন্য ছবি আপলোড করুন",
      hudTitle: "ভিশন_ইন্টেলিজেন্স_এইচইউডি"
    },
    ml: {
      title: "ഇല & വിള എഐ അനലൈസർ",
      description: "YOLOv11 & SAM2 സസ്യ കോശ രോഗനിർണ്ണയം",
      dragText: "ഇലയുടെ ചിത്രം ഇവിടെ വലിച്ചിടുക അല്ലെങ്കിൽ ബ്രൗസ് ചെയ്യുക",
      analyzing: "സസ്യ കോശങ്ങൾ പരിശോധിക്കുന്നു...",
      confidence: "വിശ്വാസ്യത സ്കോർ",
      severity: "തീവ്രത നില",
      remedy: "ഉടൻ ചെയ്യേണ്ട പ്രതിവിധി",
      uploadNew: "മറ്റൊരു ഫോട്ടോ അപ്‌ലോഡ് ചെയ്യുക",
      hudTitle: "വിഷൻ_ഇന്റലിജൻസ്_ഹഡ്"
    },
    or: {
      title: "ପତ୍ର ଓ ଫସଲ ଏଆଇ ବିଶ୍ଳେଷକ",
      description: "YOLOv11 & SAM2 ଗଛର ଟିସୁ ରୋଗ ନିରୂପଣ",
      dragText: "ପତ୍ରର ଫଟୋ ଟାଣି ଏଠାରେ ରଖନ୍ତୁ କିମ୍ବା ଫାଇଲ ଖୋଜନ୍ତୁ",
      analyzing: "ଗଛର ଟିସୁ ସ୍କାନିଂ ଚାលିଛି...",
      confidence: "ଆତ୍ମବିଶ୍ୱାସ ସ୍କୋର",
      severity: "ତୀବ୍ରତା ସ୍ତਰ",
      remedy: "ତୁରନ୍ତ ପଦକ୍ଷେପ ଗ୍ରହଣ କରନ୍ତୁ",
      uploadNew: "ଅନ୍ୟ ଏକ ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ",
      hudTitle: "ଭିଜନ_ଇଣ୍ଟେଲିଜେନ୍ସ_ଏଚୟୁଡି"
    }
  };

  const t = labels[activeLanguage] || labels["en"];
  const visionText: Record<string, {
    description: string;
    invalidImage: string;
    analysisFailed: string;
    noLeaf: string;
    clearPhoto: string;
  }> = {
    en: { description: "YOLOv8s Leaf Detection", invalidImage: "Please select a JPG, PNG, or WEBP image.", analysisFailed: "Vision analysis failed. Please try again.", noLeaf: "No leaf detected in this image.", clearPhoto: "Try a clear photo with the leaf fully visible." },
    hi: { description: "YOLOv8s पत्ती पहचान", invalidImage: "कृपया JPG, PNG या WEBP छवि चुनें।", analysisFailed: "दृश्य विश्लेषण विफल हुआ। कृपया फिर से प्रयास करें।", noLeaf: "इस छवि में कोई पत्ती नहीं मिली।", clearPhoto: "पत्ती पूरी तरह दिखाई देने वाली स्पष्ट फोटो लें।" },
    pa: { description: "YOLOv8s ਪੱਤਾ ਪਛਾਣ", invalidImage: "ਕਿਰਪਾ ਕਰਕੇ JPG, PNG ਜਾਂ WEBP ਤਸਵੀਰ ਚੁਣੋ।", analysisFailed: "ਦ੍ਰਿਸ਼ਟੀ ਵਿਸ਼ਲੇਸ਼ਣ ਅਸਫਲ ਹੋਇਆ। ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।", noLeaf: "ਇਸ ਤਸਵੀਰ ਵਿੱਚ ਕੋਈ ਪੱਤਾ ਨਹੀਂ ਮਿਲਿਆ।", clearPhoto: "ਪੱਤੇ ਦੀ ਪੂਰੀ ਤਰ੍ਹਾਂ ਸਾਫ਼ ਤਸਵੀਰ ਲਓ।" },
    mr: { description: "YOLOv8s पान ओळख", invalidImage: "कृपया JPG, PNG किंवा WEBP प्रतिमा निवडा.", analysisFailed: "दृश्य विश्लेषण अयशस्वी झाले. पुन्हा प्रयत्न करा.", noLeaf: "या प्रतिमेत कोणतेही पान आढळले नाही.", clearPhoto: "पान पूर्णपणे दिसणारा स्पष्ट फोटो घ्या." },
    te: { description: "YOLOv8s ఆకు గుర్తింపు", invalidImage: "దయచేసి JPG, PNG లేదా WEBP చిత్రాన్ని ఎంచుకోండి.", analysisFailed: "దృశ్య విశ్లేషణ విఫలమైంది. మళ్లీ ప్రయత్నించండి.", noLeaf: "ఈ చిత్రంలో ఆకు కనిపించలేదు.", clearPhoto: "ఆకు పూర్తిగా కనిపించే స్పష్టమైన ఫోటోను ప్రయత్నించండి." },
    ta: { description: "YOLOv8s இலை கண்டறிதல்", invalidImage: "JPG, PNG அல்லது WEBP படத்தைத் தேர்ந்தெடுக்கவும்.", analysisFailed: "காட்சி பகுப்பாய்வு தோல்வியடைந்தது. மீண்டும் முயற்சிக்கவும்.", noLeaf: "இந்தப் படத்தில் இலை எதுவும் கண்டறியப்படவில்லை.", clearPhoto: "இலை முழுமையாகத் தெரியும் தெளிவான புகைப்படத்தை முயற்சிக்கவும்." },
    kn: { description: "YOLOv8s ಎಲೆ ಪತ್ತೆ", invalidImage: "ದಯವಿಟ್ಟು JPG, PNG ಅಥವಾ WEBP ಚಿತ್ರವನ್ನು ಆಯ್ಕೆಮಾಡಿ.", analysisFailed: "ದೃಶ್ಯ ವಿಶ್ಲೇಷಣೆ ವಿಫಲವಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.", noLeaf: "ಈ ಚಿತ್ರದಲ್ಲಿ ಯಾವುದೇ ಎಲೆ ಕಂಡುಬಂದಿಲ್ಲ.", clearPhoto: "ಎಲೆ ಸಂಪೂರ್ಣವಾಗಿ ಕಾಣುವ ಸ್ಪಷ್ಟ ಚಿತ್ರವನ್ನು ಪ್ರಯತ್ನಿಸಿ." },
    gu: { description: "YOLOv8s પર્ણ ઓળખ", invalidImage: "કૃપા કરીને JPG, PNG અથવા WEBP છબી પસંદ કરો.", analysisFailed: "વિઝન વિશ્લેષણ નિષ્ફળ ગયું. ફરી પ્રયાસ કરો.", noLeaf: "આ છબીમાં કોઈ પાન મળ્યું નથી.", clearPhoto: "પાન સંપૂર્ણ દેખાય તેવી સ્પષ્ટ છબી અજમાવો." },
    bn: { description: "YOLOv8s পাতা শনাক্তকরণ", invalidImage: "দয়া করে JPG, PNG বা WEBP ছবি নির্বাচন করুন।", analysisFailed: "দৃশ্য বিশ্লেষণ ব্যর্থ হয়েছে। আবার চেষ্টা করুন।", noLeaf: "এই ছবিতে কোনো পাতা শনাক্ত হয়নি।", clearPhoto: "পাতাটি সম্পূর্ণ দেখা যায় এমন পরিষ্কার ছবি তুলুন।" },
    ml: { description: "YOLOv8s ഇല കണ്ടെത്തൽ", invalidImage: "JPG, PNG അല്ലെങ്കിൽ WEBP ചിത്രം തിരഞ്ഞെടുക്കുക.", analysisFailed: "വിഷൻ വിശകലനം പരാജയപ്പെട്ടു. വീണ്ടും ശ്രമിക്കുക.", noLeaf: "ഈ ചിത്രത്തിൽ ഇലയൊന്നും കണ്ടെത്തിയില്ല.", clearPhoto: "ഇല പൂർണ്ണമായി കാണുന്ന വ്യക്തമായ ചിത്രം ഉപയോഗിക്കുക." },
    or: { description: "YOLOv8s ପତ୍ର ଚିହ୍ନଟ", invalidImage: "ଦୟାକରି JPG, PNG କିମ୍ବା WEBP ଚିତ୍ର ବାଛନ୍ତୁ।", analysisFailed: "ଭିଜନ୍ ବିଶ୍ଳେଷଣ ବିଫଳ ହେଲା। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।", noLeaf: "ଏହି ଚିତ୍ରରେ କୌଣସି ପତ୍ର ମିଳିଲା ନାହିଁ।", clearPhoto: "ପତ୍ରଟି ସମ୍ପୂର୍ଣ୍ଣ ଦେଖାଯାଉଥିବା ସ୍ପଷ୍ଟ ଫଟୋ ନିଅନ୍ତୁ।" }
  };
  const vt = visionText[activeLanguage] || visionText.en;
  const displayedDetections = analysisResult?.detections
    ? Object.values(
        analysisResult.detections.reduce((grouped: Record<string, any>, detection: any) => {
          const current = grouped[detection.label];
          if (!current || detection.confidence > current.confidence) {
            grouped[detection.label] = detection;
          }
          return grouped;
        }, {})
      )
    : [];

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processImage(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      processImage(e.target.files[0]);
    }
  };

  const processImage = async (file: File) => {
    if (!file.type.startsWith("image/")) {
      setAnalysisError(vt.invalidImage);
      return;
    }

    setSelectedImage(URL.createObjectURL(file));
    setIsAnalyzing(true);
    setAnalysisResult(null);
    setAnalysisError(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("language", activeLanguage);

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiBaseUrl}/api/vision/analyze`, {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        await res.json().catch(() => null);
        throw new Error(vt.analysisFailed);
      }
      
      const data = await res.json();
      setAnalysisResult({
        image_url: data.image_url.startsWith("http")
          ? data.image_url
          : `${apiBaseUrl}${data.image_url}`,
        detections: data.detections || [],
        device: data.device,
        model: data.model
      });
      setIsAnalyzing(false);
      const firstDetection = data.detections?.[0];
      onAnalyzeComplete({
        ...data,
        vision_results: firstDetection ? {
          target: "Detected leaf",
          disease: firstDetection.label,
          confidence: firstDetection.confidence,
          severity: firstDetection.severity,
          remedy: firstDetection.remedy
        } : undefined
      });

    } catch (err) {
      setIsAnalyzing(false);
      setAnalysisError(vt.analysisFailed);
    }
  };

  const resetUpload = () => {
    setSelectedImage(null);
    setAnalysisResult(null);
    setAnalysisError(null);
  };

  return (
    <div className="glass-panel p-6 flex flex-col justify-between h-full bg-gradient-to-tr from-fuchsia-950/10 via-black/40 to-transparent border border-white/10 rounded-3xl text-left select-none relative overflow-hidden">
      
      {/* Background glowing sweep */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-fuchsia-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="shrink-0 border-b border-white/5 pb-4 mb-4">
        <h2 className="text-lg font-extrabold flex items-center gap-2 text-white">
          <Camera className="text-fuchsia-500 animate-pulse" size={20} />
          {t.title}
        </h2>
        <p className="text-xs text-fuchsia-400/80 mt-1">        {vt.description}</p>
      </div>

      <div className="flex-1 flex flex-col justify-center min-h-0">
        {!selectedImage && (
          <label 
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`w-full border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 min-h-[280px] ${
              dragActive 
                ? 'border-fuchsia-500 bg-fuchsia-500/10 shadow-[0_0_20px_rgba(217,70,239,0.2)]' 
                : 'border-white/10 hover:border-fuchsia-500/50 hover:bg-fuchsia-950/10'
            }`}
          >
            <input type="file" className="hidden" accept="image/*" onChange={handleChange} />
            <div className="w-14 h-14 rounded-full bg-fuchsia-950/50 flex items-center justify-center border border-fuchsia-500/20 mb-3 group-hover:scale-105 transition-transform">
              <Upload className="text-fuchsia-400 animate-bounce" style={{ animationDuration: '3s' }} size={24} />
            </div>
            <p className="text-xs text-center font-bold text-fuchsia-300 font-mono tracking-wide">{t.dragText}</p>
            <span className="text-[9px] text-zinc-500 uppercase tracking-widest mt-2 font-mono">JPG, PNG, WEBP</span>
          </label>
        )}

        {selectedImage && isAnalyzing && (
          <div className="w-full flex flex-col items-center justify-center py-8 min-h-[280px]">
            <div className="w-40 h-40 rounded-2xl relative overflow-hidden border border-fuchsia-500/25 shadow-lg shadow-fuchsia-950/20 mb-4">
              <img src={selectedImage} alt="Crop Leaf" className="w-full h-full object-cover blur-sm" />
              {/* Animated scanning laser line */}
              <div className="absolute inset-x-0 h-0.5 bg-fuchsia-400 animate-[bounce_2s_infinite] top-0 shadow-[0_0_8px_#d946ef]" />
              <div className="absolute inset-0 bg-gradient-to-b from-transparent via-fuchsia-500/10 to-transparent" />
            </div>
            <div className="flex items-center gap-2">
              <RefreshCw className="animate-spin text-fuchsia-500" size={14} />
              <p className="text-xs font-bold text-fuchsia-300 animate-pulse font-mono tracking-wide">{t.analyzing}</p>
            </div>
          </div>
        )}

        {selectedImage && !isAnalyzing && analysisResult && (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start w-full">
            
            {/* Visual HUD Overlay Column */}
            <div className="relative md:col-span-5 w-full h-60 bg-[#020302] rounded-2xl overflow-hidden border border-white/10 shrink-0 shadow-inner group">
              <img 
                src={analysisResult.image_url || selectedImage}
                alt="Leaf scan result" 
                className="w-full h-full object-contain" 
              />
              
              {/* Glowing Corner HUD brackets */}
              <div className="absolute top-2 left-2 border-t-2 border-l-2 border-fuchsia-500/60 w-3 h-3" />
              <div className="absolute top-2 right-2 border-t-2 border-r-2 border-fuchsia-500/60 w-3 h-3" />
              <div className="absolute bottom-2 left-2 border-b-2 border-l-2 border-fuchsia-500/60 w-3 h-3" />
              <div className="absolute bottom-2 right-2 border-b-2 border-r-2 border-fuchsia-500/60 w-3 h-3" />

              <div className="absolute top-2 left-6 text-[8px] font-mono font-bold text-fuchsia-400 uppercase tracking-widest bg-black/70 px-2 py-0.5 rounded border border-white/5 select-none">
                {t.hudTitle}
              </div>

            </div>

            {/* Analysis Text & Remedy Column */}
            <div className="md:col-span-7 space-y-3">
              {displayedDetections.map((det: any, i: number) => (
                <div key={i} className="bg-fuchsia-955/10 border border-white/5 rounded-2xl p-4 space-y-3.5 font-mono text-left relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-24 h-24 bg-fuchsia-500/[0.02] rounded-full blur-2xl pointer-events-none" />
                  
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-extrabold text-white flex items-center gap-1.5">
                      <HeartPulse size={14} className="text-red-500 animate-pulse" />
                      {det.label}
                    </span>
                    <span className="bg-red-500/10 border border-red-500/30 text-red-400 font-black px-2 py-0.5 rounded-xl text-[9px] uppercase tracking-wide">
                      {t.severity}: {det.severity}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[8px] text-fuchsia-400 font-bold uppercase tracking-wider">
                      <span>{t.confidence}</span>
                      <span>{(det.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-[#0a0f0c] h-1.5 rounded-full overflow-hidden border border-white/5">
                      <div className="bg-fuchsia-500 h-full rounded-full transition-all duration-1000" style={{ width: `${det.confidence * 100}%` }}></div>
                    </div>
                  </div>

                  {/* Immediate Remedy Container */}
                  <div className="vision-remedy-box rounded-xl p-3.5 flex items-start gap-3 shadow-sm">
                    <AlertTriangle className="vision-remedy-icon shrink-0 mt-0.5" size={14} />
                    <div className="space-y-0.5">
                      <span className="vision-remedy-label text-[8px] font-bold block uppercase tracking-widest">{t.remedy}</span>
                      <p className="vision-remedy-copy text-xs font-sans font-medium leading-relaxed select-text">{det.remedy}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {selectedImage && !isAnalyzing && displayedDetections.length === 0 && (
          <div className="w-full min-h-[280px] flex flex-col items-center justify-center rounded-2xl border border-amber-500/20 bg-amber-950/10 p-8 text-center">
            <AlertTriangle className="text-amber-400 mb-3" size={24} />
            <p className="text-sm font-bold text-amber-300">{vt.noLeaf}</p>
            <p className="text-[10px] text-zinc-500 mt-2">{vt.clearPhoto}</p>
          </div>
        )}

        {analysisError && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-950/20 p-3 text-xs font-medium text-red-300">
            {analysisError}
          </div>
        )}
      </div>

      {selectedImage && !isAnalyzing && (
        <button 
          onClick={resetUpload}
          className="mt-4 w-full bg-fuchsia-950/60 hover:bg-fuchsia-900/80 text-fuchsia-400 border border-fuchsia-500/20 font-bold py-2 rounded-xl text-xs transition-all flex items-center justify-center gap-1.5 font-mono cursor-pointer shrink-0 hover:shadow-[0_0_12px_rgba(217,70,239,0.1)]"
        >
          <ShieldCheck size={14} />
          {t.uploadNew}
        </button>
      )}
    </div>
  );
}
