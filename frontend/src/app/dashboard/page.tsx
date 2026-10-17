'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import {
  Sprout,
  Settings,
  MapPin,
  Cpu,
  FileText,
  Activity,
  ActivitySquare,
  LogOut,
  UserCheck,
  Globe,
  Bell,
  Code,
  MessageSquare,
  Sparkles,
  X,
  Menu,
  Layers,
  TrendingUp,
  AlertTriangle,
  Info
} from 'lucide-react';
import FarmMap from '@/components/dashboard/FarmMap';
import VoiceAssistant from '@/components/dashboard/VoiceAssistant';
import VisionAnalysis from '@/components/dashboard/VisionAnalysis';
import Marketprice from '@/components/dashboard/Marketprice';
import EmergencySOS from '@/components/dashboard/EmergencySOS';
import GovernmentSchemes from '@/components/dashboard/GovernmentSchemes';
import EducationPortal from '@/components/dashboard/EducationPortal';
import Preloader from '@/components/ui/Preloader';
import { apiFetch, ApiError } from '@/lib/api';

export default function Dashboard() {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [sessionLoading, setSessionLoading] = useState<boolean>(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [activeLanguage, setActiveLanguage] = useState<string>("en");
  const [activeTab, setActiveTab] = useState<string>("overview"); // overview | diagnostics | market | crisis
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [activeInfoTopic, setActiveInfoTopic] = useState<{title: string, desc: string} | null>(null); // overview | diagnostics | market | crisis
  const [agentOutput, setAgentOutput] = useState<any>(null);
  const [showNotificationAlert, setShowNotificationAlert] = useState<boolean>(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showNewsDropdown, setShowNewsDropdown] = useState<boolean>(false);
  const [newsItems, setNewsItems] = useState<any[]>([]);
  const [loadingNews, setLoadingNews] = useState<boolean>(false);
  const agentRequestKeyRef = useRef<string | null>(null);
  const isAuthenticatedRef = useRef(false);

  const fetchNews = async () => {
    setLoadingNews(true);
    try {
      const res = await fetch('/api/news', { credentials: 'include' });
      const data = await res.json();
      if (data.success) {
        setNewsItems(data.news);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingNews(false);
    }
  };

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 2800);
  };
  
  const [telemetry, setTelemetry] = useState<any>({
    temperature: 30,
    humidity: 75,
    soil_moisture: 48,
    soil_ph: 6.7,
    nitrogen: 178,
    phosphorus: 41,
    potassium: 215,
    water_level_pct: 65
  });

  const [farmerProfile, setFarmerProfile] = useState<any>({
    farmer_name: "Farmer",
    location: "Loading...",
    current_crop: "Tomato",
    land_size_hectares: 1.5,
    soil_type: "Loam",
    ph: 6.7,
    irrigation_type: "Drip",
    budget: "Medium",
    historical_diseases: ["Early Blight (2025)"],
    lat: 30.2115,
    lng: 74.9525
  });

  const [explanationText, setExplanationText] = useState<string>(
    "[INIT] Agriva OS v2.1 ready."
  );
  const [explanationTarget, setExplanationTarget] = useState<string | null>(null);
  const [isTypingAdvice, setIsTypingAdvice] = useState<boolean>(false);

  const queueExplanation = (text: string) => {
    setExplanationTarget(text);
  };

  useEffect(() => {
    if (explanationTarget === null) return;

    let index = 0;
    const resetTimeout = window.setTimeout(() => {
      setExplanationText('');
      setIsTypingAdvice(true);
    }, 0);
    const interval = window.setInterval(() => {
      index += 1;
      setExplanationText(explanationTarget.slice(0, index));
      if (index >= explanationTarget.length) {
        window.clearInterval(interval);
        setIsTypingAdvice(false);
      }
    }, 14);

    return () => {
      window.clearTimeout(resetTimeout);
      window.clearInterval(interval);
    };
  }, [explanationTarget]);

  const LANGUAGES = [
    { code: "en", label: "English" },
    { code: "hi", label: "हिंदी (Hindi)" },
    { code: "pa", label: "ਪੰਜਾਬੀ (Punjabi)" },
    { code: "mr", label: "मराठी (Marathi)" },
    { code: "te", label: "తెలుగు (Telugu)" },
    { code: "ta", label: "தமிழ் (Tamil)" },
    { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
    { code: "gu", label: "ગુજરાતી (Gujarati)" },
    { code: "bn", label: "বাংলা (Bengali)" },
    { code: "ml", label: "മലയാളം (Malayalam)" },
    { code: "or", label: "ଓਡ଼ਿଆ (Odia)" }
  ];

  // Localization Dictionary for Dashboard
  const localization: any = {
    en: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "My farm",
      diagnostics: "Check a crop",
      market: "Sell at the best price",
      crisis: "Safety & learning",
      title: "Your farm today",
      profileHeader: "Your farm details",
      profileSynced: "Up to date",
      healthHeader: "Farm health",
      healthLabel: "Farm health",
      calibHeader: "Soil and weather today",
      advisoryHeader: "Your farming advice",
      advisorySub: "Ready to help",
      signOut: "Sign Out",
      community: "Community Chat",
      nodeLabel: "Farm",
      regionLabel: "Your location",
      soilMoisture: "Soil moisture",
      soilPh: "Soil pH",
      soilTemp: "Temperature",
      cropLabel: "Crop",
      landLabel: "Farm size",
      restLabel: "Live sensor data"
    },
    hi: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "मेरा खेत",
      diagnostics: "फसल की जाँच",
      market: "बेहतर भाव पर बेचें",
      crisis: "सुरक्षा और सीख",
      title: "आज आपके खेत में",
      profileHeader: "आपके खेत की जानकारी",
      profileSynced: "अपडेट है",
      healthHeader: "खेत का स्वास्थ्य",
      healthLabel: "खेत का स्वास्थ्य",
      calibHeader: "मिट्टी और मौसम आज",
      advisoryHeader: "आपके लिए खेती की सलाह",
      advisorySub: "मदद के लिए तैयार",
      signOut: "साइन आउट",
      community: "सामुदायिक चैट",
      nodeLabel: "खेत",
      regionLabel: "आपका स्थान",
      soilMoisture: "मिट्टी की नमी",
      soilPh: "मिट्टी का pH",
      soilTemp: "तापमान",
      cropLabel: "फसल",
      landLabel: "खेत का आकार",
      restLabel: "सेंसर डेटा चालू"
    },
    pa: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "ਸੰਖੇਪ ਅਤੇ ਨਕਸ਼ਾ",
      diagnostics: "AI ਨਿਦਾਨ",
      market: "ਮਾਰਕੀਟ ਅਤੇ ਮੰਡੀ",
      crisis: "ਸੰਕਟ ਅਤੇ ਅਕੈਡਮੀ",
      title: "ਫਾਰਮ ਕੰਟਰੋਲ ਕੇਂਦਰ",
      profileHeader: "[ਮੈਮੋਰੀ_ਪ੍ਰੋਫਾਈਲ_01]",
      profileSynced: "ਸਿੰਕ ਕੀਤਾ",
      healthHeader: "[ਸਿਹਤ_ਮਾਪਕ]",
      healthLabel: "ਸਿਹਤ_ਸੂਚਕਾਂਕ",
      calibHeader: "[ਕੈਲੀਬਰੇਸ਼ਨ_ਕੋਆਰਡੀਨੇਟਸ]",
      advisoryHeader: "[ਫੈਸਲਾ_ਲੌਗ_ਸਲਾਹ]",
      advisorySub: "ਸਲਾਹ ਲੌਗ ਤਿਆਰ",
      signOut: "ਸਾਈਨ ਆਊਟ",
      community: "ਭਾਈਚਾਰਕ ਚੈਟ",
      nodeLabel: "ਨੋਡ",
      regionLabel: "ਖੇਤਰ",
      soilMoisture: "ਨਮੀ",
      soilPh: "ਮਿੱਟੀ pH",
      soilTemp: "ਤਾਪਮਾਨ",
      cropLabel: "ਸਰਗਰਮ_ਫਸਲ",
      landLabel: "ਜ਼ਮੀਨ_ਮਾਲਕੀ",
      restLabel: "ਟੈਲੀਮੈਟਰੀ ਸਰਗਰਮ"
    },
    mr: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "नकाशा व आढावा",
      diagnostics: "एआय निदान",
      market: "बाजार व मंडी",
      crisis: "संकट व अकादमी",
      title: "फार्म नियंत्रण केंद्र",
      profileHeader: "[स्मरण_प्रोफाइल_01]",
      profileSynced: "सिंक केलेले",
      healthHeader: "[आरोग्य_मापक]",
      healthLabel: "आरोग्य_निर्देशांक",
      calibHeader: "[कॅलिब्रेशन_गुणक]",
      advisoryHeader: "[निर्णय_नोंद_सल्ला]",
      advisorySub: "नोंदणी तयार",
      signOut: "बाहेर पडा",
      community: "चॅट रूम",
      nodeLabel: "नोड",
      regionLabel: "प्रदेश",
      soilMoisture: "ओलावा",
      soilPh: "माती पीएच",
      soilTemp: "तापमान",
      cropLabel: "सक्रिय_पीक",
      landLabel: "जमीन_धारणा",
      restLabel: "टेलीमेट्री चालू"
    },
    te: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "అవలోకనం & మ్యాప్",
      diagnostics: "AI డయాగ్నస్టిక్స్",
      market: "మార్కెట్ & మండి",
      crisis: "సంక్షోభం & అకాడమీ",
      title: "ఫార్మ్ కంట్రోల్ సెంటర్",
      profileHeader: "[ప్రొఫైల్_01]",
      profileSynced: "సమకాలీకరించబడింది",
      healthHeader: "[ఆరోగ్య_సూచిక]",
      healthLabel: "ఆరోగ్య_స్కోర్",
      calibHeader: "[అంశాంకన_సమన్వయం]",
      advisoryHeader: "[నిర్ణయ_సలహా_లాగ్]",
      advisorySub: "లాగ్స్ సిద్ధంగా ఉన్నాయి",
      signOut: "సైన్ అవుట్",
      community: "కమ్యూనిటీ చాట్",
      nodeLabel: "నోడ్",
      regionLabel: "ప్రాంతం",
      soilMoisture: "తేమ",
      soilPh: "నేల pH",
      soilTemp: "ఉష్ణోగ్రత",
      cropLabel: "సక్రియ_పంట",
      landLabel: "భూమి_పరిమాణం",
      restLabel: "టెలిమెట్రీ సక్రియంగా ఉంది"
    },
    ta: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "வரைபடம் & மேலாண்மை",
      diagnostics: "AI பகுப்பாய்வு",
      market: "சந்தை & மண்டி",
      crisis: "பேரிடர் & கல்வி",
      title: "பண்ணை கட்டுப்பாட்டு மையம்",
      profileHeader: "[விவரக்குறிப்பு_01]",
      profileSynced: "இணைக்கப்பட்டது",
      healthHeader: "[ஆரோக்கிய_மானி]",
      healthLabel: "ஆரோக்கிய_குறியீடு",
      calibHeader: "[அளவீட்டு_அமைப்புகள்]",
      advisoryHeader: "[முடிவு_ஆலோசனை_பதிவு]",
      advisorySub: "பதிவு தயார்",
      signOut: "வெளியேறு",
      community: "உரையாடல் அரங்கம்",
      nodeLabel: "முனையம்",
      regionLabel: "மண்டலம்",
      soilMoisture: "ஈரப்பதம்",
      soilPh: "மண் pH",
      soilTemp: "வெப்பநிலை",
      cropLabel: "செயலில்_உள்ள_பயிர்",
      landLabel: "நில_அளவு",
      restLabel: "தொலைத்தொடர்பு செயலில் உள்ளது"
    },
    kn: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "ಅವಲೋಕನ & ನಕ್ಷೆ",
      diagnostics: "AI ರೋಗನಿರ್ಣಯ",
      market: "ಮಾರುಕಟ್ಟೆ & ಮಂಡಿ",
      crisis: "ಬಿಕ್ಕಟ್ಟು & ಅಕಾಡೆಮಿ",
      title: "ಕೃಷಿ ನಿಯಂತ್ರಣ ಕೇಂದ್ರ",
      profileHeader: "[ಪ್ರೊಫೈಲ್_01]",
      profileSynced: "ಸಮನ್ವಯಗೊಂಡಿದೆ",
      healthHeader: "[ಆರೋಗ್ಯ_ಮಾನಕ]",
      healthLabel: "ಆರೋಗ್ಯ_ಸೂಚ್ಯಂಕ",
      calibHeader: "[ಅಂಶಾಂಕನ_ಅಕ್ಷಾಂಶ]",
      advisoryHeader: "[ಸಲಹಾ_ದಾಖಲೆ]",
      advisorySub: "ದಾಖಲೆಗಳು ಸಿದ್ಧ",
      signOut: "ಸೈನ್ ಔಟ್",
      community: "ಸಮುದಾಯ ಚರ್ಚೆ",
      nodeLabel: "ನೋಡ್",
      regionLabel: "ಪ್ರದೇಶ",
      soilMoisture: "ತೇವಾಂಶ",
      soilPh: "ಮಣ್ಣಿನ pH",
      soilTemp: "ತಾಪಮಾನ",
      cropLabel: "ಸಕ್ರಿಯ_ಬೆಳೆ",
      landLabel: "ಭೂಮಿಯ_ಅಳತೆ",
      restLabel: "ಟೆಲಿಮೆಟ್ರಿ ಸಕ್ರಿಯವಾಗಿದೆ"
    },
    gu: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "નકશો અને વિહંગાવલોકન",
      diagnostics: "AI નિદાન",
      market: "બજાર અને મંડી",
      crisis: "કટોકટી અને એકેડેમી",
      title: "ફાર્મ કંટ્રોલ સેન્ટર",
      profileHeader: "[પ્રોફાઇલ_01]",
      profileSynced: "સિંક થયેલ",
      healthHeader: "[આરોગ્ય_માપક]",
      healthLabel: "આરોગ્ય_આંક",
      calibHeader: "[કેલિબ્રેશન_માપદંડ]",
      advisoryHeader: "[નિર્ણય_સલાહ_લોગ]",
      advisorySub: "લોગ તૈયાર છે",
      signOut: "સાઇન આઉટ",
      community: "સમુદાય ચર્ચા",
      nodeLabel: "નોડ",
      regionLabel: "વિસ્તાર",
      soilMoisture: "ભેજ",
      soilPh: "જમીન pH",
      soilTemp: "તાપમાન",
      cropLabel: "સક્રિય_પાક",
      landLabel: "જમીન_ધારણા",
      restLabel: "ટેલિમેટ્રી સક્રિય છે"
    },
    bn: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "সারসংক্ষেপ ও মানচিত্র",
      diagnostics: "এআই রোগ নির্ণয়",
      market: "বাজার ও মান্ডি",
      crisis: "জরুরী ও একাডেমী",
      title: "খামার নিয়ন্ত্রণ কেন্দ্র",
      profileHeader: "[প্রোফাইল_০১]",
      profileSynced: "সংযুক্ত",
      healthHeader: "[স্বাস্থ্য_পরিমাপক]",
      healthLabel: "স্বাস্থ্য_সূচক",
      calibHeader: "[ক্যালিব্রেশন_প্যারামিটার]",
      advisoryHeader: "[সিদ্ধান্ত_পরামর্শ_লগ]",
      advisorySub: "পরামর্শ লগ প্রস্তুত",
      signOut: "সাইন আউট",
      community: "সম্প্রদায় চ্যাট",
      nodeLabel: "নোড",
      regionLabel: "অঞ্চল",
      soilMoisture: "আর্দ্রতা",
      soilPh: "মাটি pH",
      soilTemp: "তাপমাত্রা",
      cropLabel: "সক্রিয়_ফসল",
      landLabel: "জমির_পরিমাণ",
      restLabel: "টেলিমিট্রি সক্রিয়"
    },
    ml: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "അവലോകനം & ഭൂപടം",
      diagnostics: "AI രോഗനിർണ്ണയം",
      market: "വിപണി & മണ്ടി",
      crisis: "അടിയന്തിരം & അക്കാദമി",
      title: "ഫാം കൺട്രോൾ സെന്റർ",
      profileHeader: "[പ്രൊഫൈൽ_01]",
      profileSynced: "കണക്റ്റുചെയ്‌തു",
      healthHeader: "[ആരോഗ്യ_മാപിനി]",
      healthLabel: "ആരോഗ്യ_സൂചിക",
      calibHeader: "[അളവുകൾ]",
      advisoryHeader: "[തീരുമാന_രേഖ]",
      advisorySub: "രേഖകൾ തയ്യാറാണ്",
      signOut: "സൈൻ ഔട്ട്",
      community: "കമ്മ്യൂണിറ്റി ചാറ്റ്",
      nodeLabel: "നോഡ്",
      regionLabel: "മേഖല",
      soilMoisture: "ഈർപ്പം",
      soilPh: "മണ്ണ് pH",
      soilTemp: "താപനില",
      cropLabel: "സജീവ_വിള",
      landLabel: "ഭൂമിയുടെ_അളവ്",
      restLabel: "ടെലിമെട്രി സജീവമാണ്"
    },
    or: {
      tagline: "खेती होगी स्मार्ट, भविष्य होगा मजबूत.",
      overview: "ସଂକ୍ଷିପ୍ତ ବିବରଣୀ & ମାନଚିତ୍ର",
      diagnostics: "AI ରୋଗ ନିରୂପଣ",
      market: "ବଜାର & ମଣ୍ଡି",
      crisis: "ଆପଦକାଳୀନ & ଏକାଡେମୀ",
      title: "କୃଷି ନିୟନ୍ତ୍ରଣ କେନ୍ଦ୍ର",
      profileHeader: "[ପ୍ରୋଫାଇଲ୍_୦୧]",
      profileSynced: "ସଂଯୁକ୍ତ",
      healthHeader: "[ସ୍ୱାସ୍ଥ୍ୟ_ମାପକ]",
      healthLabel: "ସ୍ୱାସ୍ଥ್ಯ_ସୂଚକାଙ୍କ",
      calibHeader: "[କ୍ୟାଲିବ୍ରେସନ୍]",
      advisoryHeader: "[ଫୈସଲା_ପରାମର୍ଶ_ଲଗ୍]",
      advisorySub: "ଲଗ୍ ପ୍ରସ୍ତୁତ ଅଛି",
      signOut: "ସାଇନ୍ ଆଉଟ୍",
      community: "ସମୁଦାୟ ଚାଟ୍",
      nodeLabel: "ନୋଡ୍",
      regionLabel: "ଅଞ୍ଚଳ",
      soilMoisture: "ଆଦ୍ରତା",
      soilPh: "ମାଟି pH",
      soilTemp: "ତାପମାତ୍ରା",
      cropLabel: "ସକ୍ରିୟ_ଫସଲ",
      landLabel: "ଜମି_ପରିମାଣ",
      restLabel: "ଟେଲିମେଟ୍ରି ସକ୍ରିಯ"
    }
  };

  const d = localization[activeLanguage] || localization["en"];
  const quickActions: Record<string, {
    advice: string;
    adviceDesc: string;
    price: string;
    priceDesc: string;
    details: string;
    detailsDesc: string;
  }> = {
    en: { advice: "Ask for crop advice", adviceDesc: "Speak, type, or upload a leaf photo", price: "Check today's price", priceDesc: "Compare nearby mandi rates", details: "Update farm details", detailsDesc: "Keep advice accurate for your field" },
    hi: { advice: "फसल की सलाह लें", adviceDesc: "बोलें, लिखें या पत्ते की फोटो अपलोड करें", price: "आज का भाव देखें", priceDesc: "पास की मंडी के भाव की तुलना करें", details: "खेत की जानकारी अपडेट करें", detailsDesc: "अपने खेत के लिए सटीक सलाह पाएं" },
    pa: { advice: "ਫਸਲ ਦੀ ਸਲਾਹ ਲਓ", adviceDesc: "ਬੋਲੋ, ਲਿਖੋ ਜਾਂ ਪੱਤੇ ਦੀ ਫੋਟੋ ਅਪਲੋਡ ਕਰੋ", price: "ਅੱਜ ਦਾ ਭਾਅ ਦੇਖੋ", priceDesc: "ਨੇੜਲੀ ਮੰਡੀ ਦੇ ਭਾਅ ਦੀ ਤੁਲਨਾ ਕਰੋ", details: "ਖੇਤ ਦੀ ਜਾਣਕਾਰੀ ਅਪਡੇਟ ਕਰੋ", detailsDesc: "ਆਪਣੇ ਖੇਤ ਲਈ ਸਹੀ ਸਲਾਹ ਪਾਓ" },
    mr: { advice: "पिकाचा सल्ला घ्या", adviceDesc: "बोला, टाइप करा किंवा पानाचा फोटो अपलोड करा", price: "आजचा भाव पहा", priceDesc: "जवळच्या मंडीच्या दरांची तुलना करा", details: "शेताची माहिती अपडेट करा", detailsDesc: "तुमच्या शेतासाठी अचूक सल्ला मिळवा" },
    te: { advice: "పంట సలహా అడగండి", adviceDesc: "మాట్లాడండి, టైప్ చేయండి లేదా ఆకు ఫోటోను అప్‌లోడ్ చేయండి", price: "నేటి ధర చూడండి", priceDesc: "సమీప మండి ధరలను పోల్చండి", details: "పొలం వివరాలను అప్‌డేట్ చేయండి", detailsDesc: "మీ పొలానికి ఖచ్చితమైన సలహా పొందండి" },
    ta: { advice: "பயிர் ஆலோசனை கேளுங்கள்", adviceDesc: "பேசுங்கள், தட்டச்சு செய்யுங்கள் அல்லது இலைப் புகைப்படத்தைப் பதிவேற்றுங்கள்", price: "இன்றைய விலையைப் பாருங்கள்", priceDesc: "அருகிலுள்ள மண்டி விலைகளை ஒப்பிடுங்கள்", details: "பண்ணை விவரங்களைப் புதுப்பிக்கவும்", detailsDesc: "உங்கள் வயலுக்கு துல்லியமான ஆலோசனை பெறுங்கள்" },
    kn: { advice: "ಬೆಳೆ ಸಲಹೆ ಕೇಳಿ", adviceDesc: "ಮಾತನಾಡಿ, ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಎಲೆಯ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ", price: "ಇಂದಿನ ಬೆಲೆ ನೋಡಿ", priceDesc: "ಹತ್ತಿರದ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳನ್ನು ಹೋಲಿಸಿ", details: "ಹೊಲದ ವಿವರಗಳನ್ನು ನವೀಕರಿಸಿ", detailsDesc: "ನಿಮ್ಮ ಹೊಲಕ್ಕೆ ನಿಖರ ಸಲಹೆ ಪಡೆಯಿರಿ" },
    gu: { advice: "પાકની સલાહ પૂછો", adviceDesc: "બોલો, ટાઇપ કરો અથવા પાનનો ફોટો અપલોડ કરો", price: "આજનો ભાવ જુઓ", priceDesc: "નજીકની મંડીઓના ભાવની સરખામણી કરો", details: "ખેતરની વિગતો અપડેટ કરો", detailsDesc: "તમારા ખેતર માટે સચોટ સલાહ મેળવો" },
    bn: { advice: "ফসলের পরামর্শ নিন", adviceDesc: "বলুন, টাইপ করুন বা পাতার ছবি আপলোড করুন", price: "আজকের দাম দেখুন", priceDesc: "কাছের মাণ্ডির দাম তুলনা করুন", details: "খেতের তথ্য আপডেট করুন", detailsDesc: "আপনার খেতের জন্য সঠিক পরামর্শ পান" },
    ml: { advice: "വിളയുടെ ഉപദേശം ചോദിക്കുക", adviceDesc: "സംസാരിക്കുകയോ ടൈപ്പ് ചെയ്യുകയോ ഇലയുടെ ചിത്രം അപ്‌ലോഡ് ചെയ്യുകയോ ചെയ്യുക", price: "ഇന്നത്തെ വില കാണുക", priceDesc: "അടുത്തുള്ള മണ്ടി വിലകൾ താരതമ്യം ചെയ്യുക", details: "കൃഷിയിട വിവരങ്ങൾ പുതുക്കുക", detailsDesc: "നിങ്ങളുടെ കൃഷിയിടത്തിന് കൃത്യമായ ഉപദേശം നേടുക" },
    or: { advice: "ଫସଲ ପରାମର୍ଶ ନିଅନ୍ତୁ", adviceDesc: "କୁହନ୍ତୁ, ଟାଇପ୍ କରନ୍ତୁ କିମ୍ବା ପତ୍ରର ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ", price: "ଆଜିର ଦର ଦେଖନ୍ତୁ", priceDesc: "ନିକଟସ୍ଥ ମଣ୍ଡି ଦର ତୁଳନା କରନ୍ତୁ", details: "ଚାଷ ଜମିର ବିବରଣୀ ଅପଡେଟ୍ କରନ୍ତୁ", detailsDesc: "ଆପଣଙ୍କ ଜମି ପାଇଁ ସଠିକ୍ ପରାମର୍ଶ ପାଆନ୍ତୁ" }
  };
  const quickAction = quickActions[activeLanguage] || quickActions.en;

  // Authenticate session on load
  useEffect(() => {
    let active = true;
    apiFetch<{ profile?: any }>('/api/auth/me')
      .then((data) => {
        if (!active) return;
        if (data.profile) setFarmerProfile((current: any) => ({ ...current, ...data.profile }));
        isAuthenticatedRef.current = true;
        setIsAuthenticated(true);
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          router.replace('/auth');
        } else {
          setAuthError(error instanceof Error ? error.message : 'Could not secure your session.');
        }
      })
      .finally(() => {
        if (active) setSessionLoading(false);
      });

    return () => {
      active = false;
    };
  }, [router]);

  const handleSignOut = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Sign out failed:', error);
    } finally {
      isAuthenticatedRef.current = false;
      setIsAuthenticated(false);
      router.replace('/auth');
    }
  };

  // Retrieve live multi-agent telemetry once for each profile/language state.
  useEffect(() => {
    let active = true;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    const requestKey = [
      activeLanguage,
      farmerProfile.current_crop || 'Rice',
      farmerProfile.location || 'Noida'
    ].join('|');

    if (agentRequestKeyRef.current === requestKey) {
      return () => {
        active = false;
        if (retryTimeout) clearTimeout(retryTimeout);
      };
    }

    agentRequestKeyRef.current = requestKey;

    const fetchInitialAgentData = async (retryCount = 0) => {
      if (farmerProfile.location === "Loading...") return;
      try {
          const data = await apiFetch<any>('/api/chat', {
            method: "POST",
            json: {
            query: `telemetry status update for current crop ${farmerProfile.current_crop || 'Rice'} at ${farmerProfile.location || 'Noida'}`,
            language: activeLanguage,
            profile: farmerProfile
            }
          });
          if (data && active) {
          setAgentOutput(data);
          if (data.explanation) {
            queueExplanation(data.explanation);
          }
          if (data.soil_data) {
            setTelemetry({
              soil_moisture: data.soil_data.moisture,
              soil_ph: data.soil_data.ph,
              temperature: data.weather_info?.temperature || telemetry.temperature
            });
          }
        }
      } catch (e) {
        console.error("Initial agent load error:", e);
        if (retryCount < 3 && active) {
          console.log(`Retrying agent query (${retryCount + 1}/3) in 3s...`);
          retryTimeout = setTimeout(() => {
            fetchInitialAgentData(retryCount + 1);
          }, 3000);
        }
      }
    };

    if (isAuthenticated && farmerProfile.location !== "Loading...") {
      fetchInitialAgentData();
    }

    return () => {
      active = false;
      if (retryTimeout) clearTimeout(retryTimeout);
    };
  }, [isAuthenticated, activeLanguage, farmerProfile.current_crop, farmerProfile.location]);

  // Voice input is owned by VoiceAssistant and starts only after the farmer
  // presses its microphone button. A second always-on recognizer here used to
  // compete for the microphone and swallow diagnostic commands.

  const handleTelemetrySliderChange = async (key: string, val: number) => {
    const updated = { ...telemetry, [key]: val };
    setTelemetry(updated);

    try {
      await apiFetch('/api/iot/telemetry', {
        method: "POST",
        json: updated,
      });
    } catch (e) {}
  };

  const handleAgentTrigger = (data: any) => {
    if (data.soil_data) {
      setTelemetry({
        soil_moisture: data.soil_data.moisture,
        soil_ph: data.soil_data.ph,
        temperature: data.weather_info?.temperature || telemetry.temperature
      });
    }
    const unifiedData = {
      ...data,
      weather_info: data.weather_info || {
        temperature: 28,
        humidity: telemetry.soil_moisture + 10,
        rain_probability: 60,
        advisory: "Foliage humidity is high. Maintain proper soil aeration."
      },
      soil_data: data.soil_data || {
        soil_type: "Clay Loam",
        ph: telemetry.soil_ph,
        moisture: telemetry.soil_moisture,
        nitrogen: 155,
        phosphorus: 40,
        potassium: 210
      },
      market_rates: data.market_rates || {
        mandi: "Local Mandi",
        price: 3200,
        best_time: "Sell Immediately"
      }
    };

    setAgentOutput(unifiedData);

    if (data.explanation) {
      queueExplanation(data.explanation);
    } else if (data.vision_results || unifiedData.vision_results) {
      const vis = data.vision_results || unifiedData.vision_results;
      const disease = vis.disease || "Early Blight (Fungal)";
      const target = vis.target || "Tomato Leaf";
      const confidence = vis.confidence ? (vis.confidence * 100).toFixed(0) : "90";
      const severity = vis.severity || "Moderate";
      const remedy = vis.remedy || "Spray Neem oil, prune lower leaves immediately, and maintain proper crop spacing.";
      
      const report = `**Agriva Autonomous Visual Analysis**\n\n- **Target Scan**: ${target}\n- **Detected Pathogen**: ${disease}\n- **Confidence**: ${confidence}%\n- **Severity**: ${severity}\n\n**Immediate Remedy Action Plan**:\n- **Treatment Protocol**: ${remedy}`;
      queueExplanation(report);
    }

    if (data.profile) {
      setFarmerProfile(data.profile);
    }
  };

  const healthScore = (() => {
    let score = 90;
    if (telemetry.soil_moisture < 30 || telemetry.soil_moisture > 85) score -= 15;
    if (telemetry.soil_ph < 5.5 || telemetry.soil_ph > 8.0) score -= 10;
    if (agentOutput?.vision_results?.disease) score -= 20;
    return score;
  })();

  if (sessionLoading || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#050806] flex items-center justify-center relative">
        <Preloader />
        <div className="text-center space-y-4 relative z-10">
          {authError ? (
            <>
              <p className="text-sm text-red-300 font-bold">{authError}</p>
              <button onClick={() => window.location.reload()} className="text-xs text-emerald-400 underline">Retry session check</button>
            </>
          ) : (
            <>
              <Cpu className="text-emerald-500 animate-spin mx-auto" size={32} />
              <p className="text-xs text-emerald-400 font-bold tracking-wider animate-pulse font-mono">[SECURING_SESSION]</p>
            </>
          )}
        </div>
      </div>
    );
  }

  const needleRotation = ((healthScore / 100) * 180) - 90;

  return (
    <div className="farmer-dashboard min-h-screen w-full bg-[#f4f7ef] text-[#18382b] relative font-sans flex flex-col md:flex-row selection:bg-emerald-500 selection:text-white">
      <Preloader />

      {/* Gridline background overlay (Visible Aesthetic Grid) */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.045)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.045)_1px,transparent_1px)] bg-[size:44px_44px] pointer-events-none z-0" />

      {/* Left Navigation Sidebar - Desktop (Floating Capsule Design w-52) */}
      <aside className="farmer-panel w-60 shrink-0 bg-white/95 border border-emerald-900/10 shadow-[0_12px_30px_rgba(32,79,51,0.10)] hidden md:flex flex-col p-5 space-y-6 h-[calc(100vh-32px)] my-4 ml-4 rounded-3xl sticky top-4 backdrop-blur-md relative z-30 select-none text-left justify-between">
        <div className="space-y-6">
          {/* Brand Logo */}
          <div 
            onClick={() => router.push("/")}
            className="flex items-center gap-2.5 cursor-pointer hover:opacity-90 transition-all select-none border-b border-white/5 pb-4"
          >
            <Image
              src="/logo.png"
              alt="Agriva logo"
              width={24}
              height={24}
              className="h-6 w-6 rounded object-contain"
            />
            <div className="flex flex-col leading-none">
              <span className="font-black text-xs text-white tracking-tight">Agriva</span>
              <span className="text-[7px] font-bold text-emerald-400 font-mono uppercase mt-0.5">
                {d.tagline}
              </span>
            </div>
          </div>

          {/* Navigation Links List (Icons + Labels visible + Help Info Buttons) */}
          <div className="space-y-1.5 flex flex-col w-full">
            <div className="flex items-center justify-between group/link w-full">
              <button 
                onClick={() => setActiveTab("overview")}
                className={`flex-1 flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold transition-all duration-300 cursor-pointer border ${
                  activeTab === 'overview' 
                    ? 'bg-emerald-500/10 text-emerald-450 border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]' 
                    : 'text-zinc-400 border-transparent hover:bg-white/5 hover:text-white'
                }`}
              >
                <Layers size={13} className={activeTab === 'overview' ? 'text-emerald-400' : 'text-zinc-500'} />
                <span>{d.overview}</span>
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "Overview & Map Portal", desc: "SYSTEM_CORE // Renders live GIS coordinates mapping, real-time weather analytics feed, soil nutrient status assay, and government schemes matched dynamically based on land holdings." }); }}
                className="p-1 rounded text-zinc-650 hover:text-emerald-400 hover:bg-emerald-500/5 transition-all opacity-40 group-hover/link:opacity-100 cursor-pointer ml-1"
              >
                <Info size={11} />
              </button>
            </div>

            <div className="flex items-center justify-between group/link w-full">
              <button 
                onClick={() => setActiveTab("diagnostics")}
                className={`flex-1 flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold transition-all duration-300 cursor-pointer border ${
                  activeTab === 'diagnostics' 
                    ? 'bg-fuchsia-500/10 text-fuchsia-450 border-fuchsia-500/20 shadow-[0_0_15px_rgba(217,70,239,0.15)]' 
                    : 'text-zinc-400 border-transparent hover:bg-white/5 hover:text-white'
                }`}
              >
                <Sparkles size={13} className={activeTab === 'diagnostics' ? 'text-fuchsia-400' : 'text-zinc-500'} />
                <span>{d.diagnostics}</span>
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "AI Multi-Agent Diagnostic", desc: "CROP_SCANNER // Allows uploading leaf imagery for computer vision pathogen detection (YOLOv11 neural network classification) and voice querying our Gemini agent oracle for treatment recommendations." }); }}
                className="p-1 rounded text-zinc-650 hover:text-fuchsia-400 hover:bg-fuchsia-500/5 transition-all opacity-40 group-hover/link:opacity-100 cursor-pointer ml-1"
              >
                <Info size={11} />
              </button>
            </div>

            <div className="flex items-center justify-between group/link w-full">
              <button 
                onClick={() => setActiveTab("market")}
                className={`flex-1 flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold transition-all duration-300 cursor-pointer border ${
                  activeTab === 'market' 
                    ? 'bg-yellow-500/10 text-yellow-450 border-yellow-500/20 shadow-[0_0_15px_rgba(234,179,8,0.15)]' 
                    : 'text-zinc-400 border-transparent hover:bg-white/5 hover:text-white'
                }`}
              >
                <TrendingUp size={13} className={activeTab === 'market' ? 'text-yellow-400' : 'text-zinc-500'} />
                <span>{d.market}</span>
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "Market & Mandi Info", desc: "MARKET_INTELLIGENCE // Pulls agricultural mandi price lists, MSP support benchmarks, demand indices, and calculates optimal sell-or-hold windows based on market trends." }); }}
                className="p-1 rounded text-zinc-650 hover:text-yellow-400 hover:bg-yellow-500/5 transition-all opacity-40 group-hover/link:opacity-100 cursor-pointer ml-1"
              >
                <Info size={11} />
              </button>
            </div>

            <div className="flex items-center justify-between group/link w-full">
              <button 
                onClick={() => setActiveTab("crisis")}
                className={`flex-1 flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold transition-all duration-300 cursor-pointer border ${
                  activeTab === 'crisis' 
                    ? 'bg-red-500/10 text-red-450 border-red-500/20 shadow-[0_0_15px_rgba(239,68,68,0.15)]' 
                    : 'text-zinc-400 border-transparent hover:bg-white/5 hover:text-white'
                }`}
              >
                <AlertTriangle size={13} className={activeTab === 'crisis' ? 'text-red-400' : 'text-zinc-500'} />
                <span>{d.crisis}</span>
              </button>
              <button 
                onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "Emergency SOS & Academy", desc: "CRISIS_MITIGATION // Houses dynamic meteorological alerts, immediate first-aid protocols for field emergencies, and interactive agricultural tutorials." }); }}
                className="p-1 rounded text-zinc-650 hover:text-red-400 hover:bg-red-500/5 transition-all opacity-40 group-hover/link:opacity-100 cursor-pointer ml-1"
              >
                <Info size={11} />
              </button>
            </div>

            <div className="flex items-center justify-between group/link w-full">
              <Link 
                href="/community"
                className="flex-1 flex items-center gap-3 px-3 py-2 rounded-xl text-[11px] font-bold text-zinc-400 hover:bg-white/5 border border-transparent transition-all duration-300"
              >
                <MessageSquare size={13} className="text-zinc-500" />
                <span>{d.community}</span>
              </Link>
              <button 
                onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "Community Chat Room", desc: "PEER_COMMUNICATION // Connects you to a live chat console to exchange agricultural insights, query local farming cooperatives, and share advice." }); }}
                className="p-1 rounded text-zinc-650 hover:text-emerald-450 hover:bg-emerald-500/5 transition-all opacity-40 group-hover/link:opacity-100 cursor-pointer ml-1"
              >
                <Info size={11} />
              </button>
            </div>
          </div>
        </div>

        {/* Sidebar Footer Controls */}
        <div className="space-y-4 pt-4 border-t border-white/5">
          {/* Sign Out */}
          <button 
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-xs font-bold text-zinc-500 hover:text-white hover:bg-red-950/20 transition-all cursor-pointer"
          >
            <LogOut size={13} className="text-zinc-500" />
            <span>{d.signOut}</span>
          </button>
        </div>
      </aside>

      {/* Mobile Drawer Navigation Backdrop */}
      {isMobileMenuOpen && (
        <div 
          onClick={() => setIsMobileMenuOpen(false)}
          className="fixed inset-0 z-45 bg-black/60 backdrop-blur-xs md:hidden animate-fade-in"
        />
      )}

      {/* Mobile Drawer Panel */}
      <aside className={`farmer-panel fixed top-0 bottom-0 left-0 w-72 bg-white border-r border-emerald-900/10 z-50 p-6 flex flex-col justify-between transition-transform duration-300 md:hidden select-none text-left ${
        isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="space-y-6">
          {/* Header Close */}
          <div className="flex justify-between items-center border-b border-white/5 pb-4">
            <div className="flex items-center gap-2">
              <Image
                src="/logo.png"
                alt="Agriva logo"
                width={24}
                height={24}
                className="h-6 w-6 rounded object-contain"
              />
              <span className="font-extrabold text-sm text-white">Agriva</span>
            </div>
            <button 
              onClick={() => setIsMobileMenuOpen(false)}
              className="p-1 rounded-lg hover:bg-white/5 text-zinc-400 hover:text-white cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>

          {/* Navigation Links */}
          <div className="space-y-2 flex flex-col">
            <button 
              onClick={() => { setActiveTab("overview"); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold cursor-pointer ${
                activeTab === 'overview' ? 'bg-emerald-500/10 text-emerald-450 border border-emerald-500/20' : 'text-zinc-400 hover:bg-white/5'
              }`}
            >
              <Layers size={14} />
              <span>{d.overview}</span>
            </button>

            <button 
              onClick={() => { setActiveTab("diagnostics"); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold cursor-pointer ${
                activeTab === 'diagnostics' ? 'bg-fuchsia-500/10 text-fuchsia-450 border border-fuchsia-500/20' : 'text-zinc-400 hover:bg-white/5'
              }`}
            >
              <Sparkles size={14} />
              <span>{d.diagnostics}</span>
            </button>

            <button 
              onClick={() => { setActiveTab("market"); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold cursor-pointer ${
                activeTab === 'market' ? 'bg-yellow-500/10 text-yellow-450 border border-yellow-500/20' : 'text-zinc-400 hover:bg-white/5'
              }`}
            >
              <TrendingUp size={14} />
              <span>{d.market}</span>
            </button>

            <button 
              onClick={() => { setActiveTab("crisis"); setIsMobileMenuOpen(false); }}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold cursor-pointer ${
                activeTab === 'crisis' ? 'bg-red-500/10 text-red-450 border border-red-500/20' : 'text-zinc-400 hover:bg-white/5'
              }`}
            >
              <AlertTriangle size={14} />
              <span>{d.crisis}</span>
            </button>

            <Link 
              href="/community"
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold text-zinc-400 hover:bg-white/5"
            >
              <MessageSquare size={14} />
              <span>{d.community}</span>
            </Link>
          </div>
        </div>

        {/* Sidebar Footer Controls */}
        <div className="space-y-4 pt-4 border-t border-white/5">
          {/* Language Selector */}
          <div className="flex items-center gap-1.5 text-zinc-400 border border-white/5 bg-black/50 p-2 rounded-xl text-[11px] font-bold">
            <Globe size={12} className="text-zinc-500" />
            <select 
              value={activeLanguage}
              onChange={(e) => setActiveLanguage(e.target.value)}
              className="bg-transparent outline-none cursor-pointer border-none text-[11px] font-bold flex-1 text-white"
            >
              {LANGUAGES.map((langOption) => (
                <option key={langOption.code} value={langOption.code} className="bg-[#050806] text-white">
                  {langOption.label}
                </option>
              ))}
            </select>
          </div>

          {/* Sign Out */}
          <button 
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-xs font-bold text-zinc-500 hover:text-white hover:bg-red-950/20 transition-all cursor-pointer"
          >
            <LogOut size={13} className="text-zinc-500" />
            <span>{d.signOut}</span>
          </button>
        </div>
      </aside>

      {/* Right Content Area Pane */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0 bg-transparent relative z-10">
        
        {/* Top Header - Floating Capsule Design (Half-Length) */}
        <header className="farmer-panel w-[calc(100%-32px)] mx-4 rounded-2xl border border-emerald-900/10 bg-white/95 backdrop-blur-md px-5 md:px-6 py-3 sticky top-4 z-30 shrink-0 select-none flex justify-between items-center shadow-[0_8px_24px_rgba(32,79,51,0.10)] mt-4">
          {/* Left Title & Mobile Hamburger */}
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsMobileMenuOpen(true)}
              className="md:hidden p-1.5 rounded-xl bg-white/5 border border-white/10 text-zinc-400 hover:text-white cursor-pointer transition-colors"
            >
              <Menu size={16} />
            </button>
            <span className={`text-sm md:text-base font-extrabold tracking-tight ${
              activeTab === 'overview' ? 'text-emerald-450' :
              activeTab === 'diagnostics' ? 'text-fuchsia-450' :
              activeTab === 'market' ? 'text-yellow-450' :
              'text-red-450'
            }`}>
              {activeTab === 'overview' ? d.overview :
               activeTab === 'diagnostics' ? d.diagnostics :
               activeTab === 'market' ? d.market :
               d.crisis}
            </span>
          </div>

          {/* Center/Right Controls: Multilingual selector, Notification Bell, User Name */}
          <div className="flex items-center gap-3">
            
            {/* Regional Language SelectDropdown (Top Navbar Only Feature) */}
            <button onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "System Locale Selector", desc: "SYSTEM_LOCALE // Adjusts display text, system notifications, speech translation modules, and generative AI responses into regional Indian scripts." }); }} className="p-1 rounded-md text-zinc-650 hover:text-white transition-colors cursor-pointer" title="Info"><Info size={11} /></button>
            <div className="bg-zinc-950/60 px-2 py-1 flex items-center gap-1.5 text-zinc-400 border border-white/10 rounded-xl text-[10.5px] font-bold">
              <Globe size={11} className={`animate-pulse ${
                activeTab === 'overview' ? 'text-emerald-400' :
                activeTab === 'diagnostics' ? 'text-fuchsia-400' :
                activeTab === 'market' ? 'text-yellow-400' :
                'text-red-400'
              }`} />
              <select 
                value={activeLanguage}
                onChange={(e) => setActiveLanguage(e.target.value)}
                className={`bg-transparent outline-none cursor-pointer border-none text-[10.5px] font-black ${
                  activeTab === 'overview' ? 'text-emerald-400' :
                  activeTab === 'diagnostics' ? 'text-fuchsia-400' :
                  activeTab === 'market' ? 'text-yellow-400' :
                  'text-red-400'
                }`}
              >
                {LANGUAGES.map((langOption) => (
                  <option key={langOption.code} value={langOption.code} className="bg-[#050806] text-white">
                    {langOption.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Notification Bell Dropdown Button */}
            <button onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "Agricultural Broadcasts", desc: "TELEMETRY_BROADCASTS // Checks and displays real-time weather alerts, sub-district emergency warnings, and live agricultural broadcasts parsed from news RSS channels." }); }} className="p-1 rounded-md text-zinc-650 hover:text-white transition-colors cursor-pointer" title="Info"><Info size={11} /></button>
            <div className="relative">
              <button
                type="button"
                aria-label="Open farm alerts"
                onClick={async () => {
                  setShowNewsDropdown(!showNewsDropdown);
                  setShowNotificationAlert(false);
                  if (!showNewsDropdown && newsItems.length === 0) {
                    await fetchNews();
                  }
                }}
                className="relative w-10 h-10 rounded-xl bg-emerald-50 hover:bg-emerald-100 flex items-center justify-center cursor-pointer border border-emerald-200 transition-colors z-40"
              >
                <Bell size={17} className="text-emerald-700" />
                {showNotificationAlert && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 border-2 border-white"></span>
                )}
              </button>

              {/* Notification Dropdown Drawer Overlay */}
              {showNewsDropdown && (
                <div className="absolute right-0 mt-3 w-80 bg-[#090d0a]/95 backdrop-blur-3xl border border-white/10 rounded-2xl shadow-[0_15px_40px_rgba(0,0,0,0.65)] p-4 z-50 text-left space-y-3">
                  <div className="flex justify-between items-center border-b border-white/5 pb-2">
                    <span className="text-[10px] font-mono font-bold text-emerald-450 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                      Agricultural Broadcasts
                    </span>
                    <button 
                      onClick={() => setShowNewsDropdown(false)}
                      className="text-zinc-500 hover:text-white transition-colors cursor-pointer"
                    >
                      <X size={12} />
                    </button>
                  </div>

                  <div className="max-h-64 overflow-y-auto space-y-2.5 pr-1 select-text">
                    {loadingNews ? (
                      <div className="py-8 text-center text-zinc-500 text-[10px] font-mono flex flex-col items-center gap-2">
                        <div className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                        <span>Fetching live telemetry news...</span>
                      </div>
                    ) : newsItems.length === 0 ? (
                      <div className="py-8 text-center text-zinc-500 text-[10px] font-mono">
                        No active broadcasts received.
                      </div>
                    ) : (
                      newsItems.map((item, idx) => (
                        <a 
                          key={idx}
                          href={item.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block p-2.5 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] hover:border-emerald-500/20 transition-all group"
                        >
                          <div className="flex justify-between items-center gap-2 mb-1">
                            <span className="text-[8px] font-mono font-bold text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/10">
                              {item.source}
                            </span>
                            <span className="text-[7.5px] text-zinc-500 font-mono">
                              {item.pubDate ? new Date(item.pubDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : ''}
                            </span>
                          </div>
                          <h4 className="text-[10px] font-sans font-medium text-zinc-200 group-hover:text-white leading-snug line-clamp-2 transition-colors">
                            {item.title}
                          </h4>
                        </a>
                      ))
                    )}
                  </div>

                  <div className="text-[7.5px] font-mono text-zinc-500 uppercase tracking-widest pt-2 border-t border-white/5 flex justify-between">
                    <span>Google News RSS</span>
                    <button onClick={fetchNews} className="text-emerald-400 hover:text-emerald-300 font-bold transition-all cursor-pointer">
                      Force Refresh
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Profile Avatar Capsule displaying Name of User */}
            <div className="flex items-center gap-2 pl-2 border-l border-white/10">
              <div className="hidden sm:flex flex-col text-right leading-tight">
                <span className="text-xs font-extrabold text-white tracking-wide">{farmerProfile.farmer_name}</span>
                <span className="text-[8px] font-mono text-zinc-500 tracking-wider">LOC: {farmerProfile.location.toUpperCase()}</span>
              </div>
              <button
                onClick={() => router.push("/profile")}
                className="p-2 rounded-xl border border-white/10 text-zinc-400 hover:text-emerald-400 hover:border-emerald-500/30 transition-colors"
                title="Edit farmer profile"
                aria-label="Edit farmer profile"
              >
                <Settings size={14} />
              </button>
              <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-450 flex items-center justify-center font-mono font-black text-xs shadow-inner animate-pulse-soft">
                {farmerProfile.farmer_name.substring(0, 2).toUpperCase()}
              </div>
            </div>

          </div>
        </header>

        {/* Scrollable Dashboard Viewport Pane */}
        <main className="flex-1 p-4 md:p-6 overflow-y-auto max-w-7xl w-full mx-auto space-y-6">
          <div className="transition-all duration-300">
          {/* TAB 1: OVERVIEW & MAP */}
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              
              {/* Dynamic Time-based Greeting Banner */}
              {(() => {
                const greetings: any = {
                   en: { morning: "Good morning", afternoon: "Good afternoon", evening: "Good evening", night: "Good night", welcome: "Here is what needs your attention today." },
                  hi: { morning: "शुभ प्रभात", afternoon: "शुभ दोपहर", evening: "शुभ संध्या", night: "शुभ रात्रि", welcome: "अपने कृषि नियंत्रण केंद्र में आपका स्वागत है।" },
                  pa: { morning: "ਸ਼ੁਭ ਸਵੇਰ", afternoon: "ਸ਼ੁਭ ਦੁਪਹਿਰ", evening: "ਸ਼ੁਭ ਸ਼ਾਮ", night: "ਸ਼ੁਭ ਰਾਤ", welcome: "ਆਪਣੇ ਖੇਤੀਬਾੜੀ ਕੰਟਰੋਲ ਕੇਂਦਰ ਵਿੱਚ ਜੀ ਆਇਆਂ ਨੂੰ।" },
                  mr: { morning: "शुभ प्रभात", afternoon: "शुभ दुपार", evening: "शुभ संध्या", night: "शुभ रात्री", welcome: "आपल्या कृषी नियंत्रण केंद्रात स्वागत आहे." },
                  te: { morning: "శుభోదయం", afternoon: "శుభ మధ్యాహ్నం", evening: "శుభ సాయంత్రం", night: "శుభ రాత్రి", welcome: "మీ వ్యవసాయ నియంత్రణ కేంద్రానికి స్వాగతం." },
                  ta: { morning: "காலை வணக்கம்", afternoon: "மதிய வணக்கம்", evening: "மாலை வணக்கம்", night: "இரவு வணக்கம்", welcome: "உங்கள் விவசாய கட்டுப்பாட்டு மையத்திற்கு வரவேற்கிறோம்." },
                  kn: { morning: "ಶುਭೋದಯ", afternoon: "ಶುਭ ಮಧ್ಯಾಹ್ನ", evening: "ಶುಭ ಸಂಜೆ", night: "ಶುਭ ರಾತ್ರಿ", welcome: "ನಿಮ್ಮ ಕೃಷಿ ನಿಯಂತ್ರಣಕ್ಕೆ ಸ್ವಾಗत." },
                  gu: { morning: "શુભ સવાર", afternoon: "શુભ બપોર", evening: "શુભ સાંજ", night: "શુભ રાત્રિ", welcome: "તમારા કૃષિ નિયંત્રણ કેન્દ્રમાં સ્વાગત છે." },
                  bn: { morning: "সুপ্রভাত", afternoon: "শুভ দুপুর", evening: "শুভ সন্ধ্যা", night: "শুভ রাত্রি", welcome: "আপনার কৃষি নিয়ন্ত্রণ কেন্দ্রে স্বাগত।" },
                  ml: { morning: "ശുഭപ്രഭാതം", afternoon: "ശുഭ ഉച്ചനേരം", evening: "ശുഭസായാഹ്നം", night: "ശുഭരാത്രി", welcome: "നിങ്ങളുടെ കാർഷിക നിയന്ത്രణ കേന്ദ്രത്തിലേക്ക് സ്വാഗതം." },
                  or: { morning: "ଶୁଭ ସକାଳ", afternoon: "ଶୁଭ ଅପରାହ୍ନ", evening: "ଶୁଭ ସନ୍ଧ୍ୟา", night: "ଶୁଭ ରାତ୍ରି", welcome: "ଆପଣଙ୍କ କୃଷି ନିୟନ୍ତ୍ରଣ କେନ୍ଦ୍ରକୁ ସ୍ୱାਗତ ।" }
                };
                const hour = new Date().getHours();
                const gLang = greetings[activeLanguage] || greetings["en"];
                let greetText = gLang.morning;
                if (hour >= 12 && hour < 17) greetText = gLang.afternoon;
                else if (hour >= 17 && hour < 21) greetText = gLang.evening;
                else if (hour >= 21 || hour < 5) greetText = gLang.night;

                return (
                   <div className="col-span-12 bg-gradient-to-r from-emerald-50 via-white to-amber-50 border border-emerald-200 p-6 rounded-3xl mb-2 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative overflow-hidden shadow-md text-left">
                    <div className="absolute -top-12 -left-12 w-32 h-32 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none" />
                    <div className="relative z-10 space-y-1">
                         <h2 className="text-xl md:text-2xl font-black farmer-heading flex items-center gap-2">
                        <span>{greetText}, {farmerProfile.farmer_name}!</span>
                           <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 border border-emerald-200 px-2.5 py-1 rounded-full tracking-wide">
                           Live update
                        </span>
                      </h2>
                       <p className="text-sm text-zinc-500 font-medium">
                        {gLang.welcome}
                      </p>
                    </div>
                     <div className="relative z-10 text-right text-xs text-zinc-500 bg-white/75 p-3 rounded-xl border border-emerald-200 space-y-1 shadow-sm">
                       <div>Updated <span className="text-emerald-800 font-bold">{new Date().toLocaleTimeString(undefined, {hour: '2-digit', minute:'2-digit'})}</span></div>
                       <div>Location: <span className="text-emerald-700 font-bold">{farmerProfile.location}</span></div>
                    </div>
                  </div>
                );
               })()}

               {/* Large, plain-language shortcuts for common farm tasks */}
               <div className="col-span-12 grid grid-cols-1 sm:grid-cols-3 gap-3">
                 <button
                   type="button"
                   onClick={() => setActiveTab("diagnostics")}
                   className="farmer-panel group flex items-center gap-3 rounded-2xl p-4 text-left transition hover:-translate-y-0.5 hover:border-emerald-300"
                 >
                   <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                     <Sparkles size={20} />
                   </span>
                   <span>
                     <span className="block text-sm font-extrabold text-emerald-950">{quickAction.advice}</span>
                     <span className="block text-xs text-zinc-500 mt-0.5">{quickAction.adviceDesc}</span>
                   </span>
                 </button>
                 <button
                   type="button"
                   onClick={() => setActiveTab("market")}
                   className="farmer-panel group flex items-center gap-3 rounded-2xl p-4 text-left transition hover:-translate-y-0.5 hover:border-amber-300"
                 >
                   <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
                     <TrendingUp size={20} />
                   </span>
                   <span>
                     <span className="block text-sm font-extrabold text-emerald-950">{quickAction.price}</span>
                     <span className="block text-xs text-zinc-500 mt-0.5">{quickAction.priceDesc}</span>
                   </span>
                 </button>
                 <Link
                   href="/profile"
                   className="farmer-panel group flex items-center gap-3 rounded-2xl p-4 text-left transition hover:-translate-y-0.5 hover:border-sky-300"
                 >
                   <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-sky-100 text-sky-700">
                     <Settings size={20} />
                   </span>
                   <span>
                     <span className="block text-sm font-extrabold text-emerald-950">{quickAction.details}</span>
                     <span className="block text-xs text-zinc-500 mt-0.5">{quickAction.detailsDesc}</span>
                   </span>
                 </Link>
               </div>

               {/* Left Column (sliders and metrics) */}
              <div className="lg:col-span-4 flex flex-col space-y-4">
                
                {/* Farmer Profile Memory Card */}
                <div className="glass-panel p-4 bg-black/40 border border-white/10">
                  <div className="flex items-center justify-between mb-3 border-b border-white/10 pb-2">
                     <span className="text-sm font-extrabold text-emerald-900 tracking-tight">{d.profileHeader}</span>
                     <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">{d.profileSynced}</span>
                  </div>

                   <div className="space-y-1.5 text-sm font-semibold text-zinc-300 text-left">
                     <div className="flex justify-between gap-3 p-2.5 bg-emerald-50 rounded border border-emerald-100">
                       <span className="text-zinc-500 text-xs">Farmer</span>
                      <span className="text-white font-bold">{farmerProfile.farmer_name}</span>
                    </div>
                    {farmerProfile.contact_number && (
                       <div className="flex justify-between gap-3 p-2.5 bg-emerald-50 rounded border border-emerald-100">
                       <span className="text-zinc-500 text-xs">Phone</span>
                        <span className="text-white font-bold">{farmerProfile.contact_number}</span>
                      </div>
                    )}
                     <div className="flex justify-between gap-3 p-2.5 bg-emerald-50 rounded border border-emerald-100">
                       <span className="text-zinc-500 text-xs">{d.regionLabel}</span>
                      <span className="text-emerald-400 font-bold">📍 {farmerProfile.location}</span>
                    </div>
                    {farmerProfile.address && (
                       <div className="flex justify-between gap-3 p-2.5 bg-emerald-50 rounded border border-emerald-100">
                       <span className="text-zinc-500 text-xs">Farm address</span>
                        <span className="text-white font-bold truncate max-w-[150px]">{farmerProfile.address}</span>
                      </div>
                    )}
                     <div className="flex justify-between gap-3 p-2.5 bg-emerald-50 rounded border border-emerald-100">
                       <span className="text-zinc-500 text-xs">{d.cropLabel}</span>
                      <span className="text-white font-bold">{farmerProfile.current_crop}</span>
                    </div>
                     <div className="flex justify-between gap-3 p-2.5 bg-emerald-50 rounded border border-emerald-100">
                       <span className="text-zinc-500 text-xs">{d.landLabel}</span>
                       <span className="text-white font-bold">{farmerProfile.land_size_hectares} hectares</span>
                    </div>
                  </div>
                </div>



                {/* Government Schemes Recommendation Card */}
                <div className="glass-panel p-4 bg-black/40 border border-white/10 shrink-0 text-left">
                  <div className="flex justify-between items-center mb-3 border-b border-white/10 pb-2">
                     <span className="text-sm font-extrabold text-emerald-900 tracking-tight">📜 Subsidies and schemes</span>
                     <span className="text-xs font-bold text-yellow-700 uppercase tracking-wide">Matched for you</span>
                  </div>
                  {agentOutput?.schemes && agentOutput.schemes.length > 0 ? (
                    <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                      {agentOutput.schemes.map((scheme: any, idx: number) => (
                         <div key={idx} className="scheme-card p-3 rounded-xl space-y-1.5">
                           <div className="text-sm font-extrabold text-white leading-snug">{scheme.name}</div>
                           <div className="text-xs text-zinc-400 font-medium leading-relaxed">{scheme.benefits}</div>
                           <div className="text-[11px] font-semibold text-emerald-450">Documents: {scheme.documents?.join(', ')}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-8 text-center text-zinc-500 text-[10px] font-mono flex flex-col items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin"></div>
                      <span>Loading matched schemes...</span>
                    </div>
                  )}
                </div>

              </div>

              {/* Right Column: Google satellite farm map and sliders calibration */}
              <div className="lg:col-span-8 flex flex-col space-y-4">
                
                <div className="h-96 w-full relative">
                  <FarmMap 
                    weather={agentOutput?.weather_info} 
                    soil={telemetry} 
                    activeLanguage={activeLanguage}
                    farmerLat={farmerProfile.lat}
                    farmerLng={farmerProfile.lng}
                    farmerAddress={[farmerProfile.address, farmerProfile.location].filter(Boolean).join(", ")}
                  />
                </div>

                {/* IoT Calibration Sliders */}
                <div className="glass-panel p-4 space-y-3 bg-black/40 border border-white/10 shrink-0 text-left">
                  <div className="flex justify-between items-center mb-1 border-b border-white/10 pb-2">
                     <span className="text-sm font-extrabold text-emerald-900 tracking-tight">{d.calibHeader}</span>
                    <button onClick={(e) => { e.stopPropagation(); setActiveInfoTopic({ title: "IoT Telemetry Calibration", desc: "TELEMETRY_READINGS // Real-time soil metrics. User overrides are disabled. Values are locked and updated by the LangGraph agents." }); }} className="p-1 rounded-md text-zinc-650 hover:text-white transition-colors cursor-pointer" title="Info"><Info size={11} /></button>
                     <span className="text-xs font-bold text-emerald-700 uppercase tracking-wide">{d.restLabel}</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-1 bg-cyan-950/10 p-2.5 rounded-xl border border-cyan-500/10 relative group/slider">
                      <div className="flex justify-between text-[9px] font-bold font-mono">
                        <span className="text-zinc-500">{d.soilMoisture}</span>
                        <span className="text-cyan-400">{telemetry.soil_moisture}%</span>
                      </div>
                      <div className="h-1 bg-zinc-950 rounded-lg overflow-hidden mt-2">
                        <div className="h-full bg-cyan-500 transition-all duration-500" style={{ width: `${telemetry.soil_moisture}%` }}></div>
                      </div>
                    </div>

                    <div className="space-y-1 bg-fuchsia-955/10 p-2.5 rounded-xl border border-fuchsia-500/10 relative group/slider">
                      <div className="flex justify-between text-[9px] font-bold font-mono">
                        <span className="text-zinc-500">{d.soilPh}</span>
                        <span className="text-fuchsia-400">{telemetry.soil_ph}</span>
                      </div>
                      <div className="h-1 bg-zinc-950 rounded-lg overflow-hidden mt-2">
                        <div className="h-full bg-fuchsia-500 transition-all duration-500" style={{ width: `${(telemetry.soil_ph / 14) * 100}%` }}></div>
                      </div>
                      {/* 7-day trend sparkline chart */}
                      <div className="pt-2 flex items-center justify-between gap-2 text-[8px] font-mono text-zinc-550 border-t border-white/5 mt-2 select-none">
                        <span>7D pH TREND:</span>
                        <svg className="w-20 h-5 stroke-fuchsia-400 fill-none" viewBox="0 0 70 20">
                          <path
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d={`M 0,${20 - (6.6 / 14) * 20} 
                               L 11,${20 - (6.7 / 14) * 20} 
                               L 22,${20 - (6.5 / 14) * 20} 
                               L 33,${20 - (6.8 / 14) * 20} 
                               L 44,${20 - (6.7 / 14) * 20} 
                               L 55,${20 - (6.6 / 14) * 20} 
                               L 70,${20 - (telemetry.soil_ph / 14) * 20}`}
                          />
                        </svg>
                      </div>
                    </div>

                    <div className="space-y-1 bg-amber-955/10 p-2.5 rounded-xl border border-amber-500/10 relative group/slider">
                      <div className="flex justify-between text-[9px] font-bold font-mono">
                        <span className="text-zinc-500">{d.soilTemp}</span>
                        <span className="text-amber-400">{telemetry.temperature}°C</span>
                      </div>
                      <div className="h-1 bg-zinc-950 rounded-lg overflow-hidden mt-2">
                        <div className="h-full bg-amber-500 transition-all duration-500" style={{ width: `${(telemetry.temperature / 50) * 100}%` }}></div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Multi-Agent Dashboard Telemetry Advisories */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                  {/* Weather Advisory */}
                  <div className="glass-panel p-4 bg-gradient-to-br from-cyan-955/15 via-black/45 to-transparent border border-cyan-500/20 rounded-2xl text-left space-y-2 shadow-md">
                    <div className="flex justify-between items-center pb-2 border-b border-white/5 font-mono text-[9px]">
                     <span className="text-cyan-700 font-bold tracking-wide">🌤️ Weather today</span>
                       <span className="text-zinc-500">Live forecast</span>
                    </div>
                    {agentOutput?.weather_info ? (
                      <div className="space-y-1.5 font-mono text-[10px]">
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Temperature</span>
                          <span className="text-cyan-400">{agentOutput.weather_info.temperature}°C</span>
                        </div>
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Humidity</span>
                          <span className="text-cyan-400">{agentOutput.weather_info.humidity}%</span>
                        </div>
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Chance of rain</span>
                          <span className="text-cyan-400">{agentOutput.weather_info.rain_probability}%</span>
                        </div>
                        <p className="text-[9px] text-amber-400 italic pt-1 leading-normal">
                           Tip: {agentOutput.weather_info.advisory}
                        </p>
                      </div>
                    ) : (
                      <div className="py-6 text-center text-zinc-600 text-[9px] font-mono animate-pulse">Scanning weather satellite...</div>
                    )}
                  </div>

                  {/* Soil Nutrient Advisory */}
                  <div className="glass-panel p-4 bg-gradient-to-br from-emerald-955/15 via-black/45 to-transparent border border-emerald-500/20 rounded-2xl text-left space-y-2 shadow-md">
                    <div className="flex justify-between items-center pb-2 border-b border-white/5 font-mono text-[9px]">
                     <span className="text-emerald-700 font-bold tracking-wide">🌱 Soil condition</span>
                       <span className="text-zinc-500">From your sensors</span>
                    </div>
                    {agentOutput?.soil_data ? (
                      <div className="space-y-1.5 font-mono text-[10px]">
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Soil type</span>
                          <span className="text-emerald-450">{agentOutput.soil_data.soil_type}</span>
                        </div>
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Soil pH</span>
                          <span className="text-fuchsia-400">{agentOutput.soil_data.ph}</span>
                        </div>
                        <div className="text-[10px] font-bold text-zinc-350 flex justify-between pt-0.5">
                           <span>Nutrients</span>
                          <span className="text-emerald-400 font-extrabold">{agentOutput.soil_data.nitrogen}N : {agentOutput.soil_data.phosphorus}P : {agentOutput.soil_data.potassium}K</span>
                        </div>
                        <p className="text-[9px] text-zinc-400 italic pt-1 leading-normal truncate" title={agentOutput.soil_data.advisory}>
                           Tip: {agentOutput.soil_data.advisory}
                        </p>
                      </div>
                    ) : (
                      <div className="py-6 text-center text-zinc-600 text-[9px] font-mono animate-pulse">Running nutrient assay...</div>
                    )}
                  </div>

                  {/* Market & Mandi Advisory */}
                  <div className="glass-panel p-4 bg-gradient-to-br from-yellow-955/15 via-black/45 to-transparent border border-yellow-500/20 rounded-2xl text-left space-y-2 shadow-md">
                    <div className="flex justify-between items-center pb-2 border-b border-white/5 font-mono text-[9px]">
                     <span className="text-yellow-700 font-bold tracking-wide">📈 Market prices</span>
                       <span className="text-zinc-500">Nearby mandi</span>
                    </div>
                    {agentOutput?.market_rates ? (
                      <div className="space-y-1.5 font-mono text-[10px]">
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Market</span>
                          <span className="text-yellow-400 truncate max-w-[90px]" title={agentOutput.market_rates.mandi}>{agentOutput.market_rates.mandi}</span>
                        </div>
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Today&apos;s price</span>
                          <span className="text-white font-extrabold">₹{agentOutput.market_rates.price}/q</span>
                        </div>
                        <div className="text-[11px] font-bold text-white flex justify-between">
                           <span>Best time to sell</span>
                          <span className="text-amber-400 font-black">{agentOutput.market_rates.best_time}</span>
                        </div>
                        <p className="text-[9px] text-zinc-450 italic pt-1 leading-normal">
                           Government support price: ₹{agentOutput.market_rates.msp || '2183'}/q
                        </p>
                      </div>
                    ) : (
                      <div className="py-6 text-center text-zinc-600 text-[9px] font-mono animate-pulse">Fetching market indexes...</div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          )}
          {/* TAB 2: AI MULTI-AGENT DIAGNOSTIC */}
          {activeTab === "diagnostics" && (
            <div className="grid grid-cols-1 gap-6 items-start pb-8 text-left">
              
              {/* Plant image analysis */}
              <VisionAnalysis
                onAnalyzeComplete={handleAgentTrigger}
                activeLanguage={activeLanguage}
              />

              {/* Voice Input & Smart Advisory Output Stacks */}
              <div className="flex flex-col gap-6 w-full">
                <VoiceAssistant 
                  onAgentTriggered={handleAgentTrigger}
                  activeLanguage={activeLanguage}
                  onLanguageChange={(langValue) => setActiveLanguage(langValue)}
                />
                
                <div className="advisory-output-panel glass-panel p-6 flex flex-col justify-between min-h-[300px] w-full rounded-3xl relative overflow-hidden select-none">
                  <div className="flex-1 min-h-0 flex flex-col">
                    <div className="advisory-output-header flex justify-between items-center mb-3 pb-2 shrink-0 font-mono">
                      <span className="text-sm font-extrabold text-emerald-900 tracking-tight">{d.advisoryHeader}</span>
                      <span className="text-xs font-bold uppercase tracking-wider">{isTypingAdvice ? 'WRITING ADVICE...' : d.advisorySub}</span>
                    </div>

                    {/* Live Visual Routing Chain Graph */}
                    {agentOutput?.execution_plan && (
                      <div className="advisory-route flex flex-wrap items-center gap-1 p-2.5 rounded-2xl mb-3 text-[7.5px] font-mono font-bold uppercase shrink-0 select-none">
                        <span className="text-zinc-500 mr-1">ROUTE:</span>
                        {agentOutput.execution_plan.map((step: string, sIdx: number) => (
                          <React.Fragment key={sIdx}>
                            {sIdx > 0 && <span className="advisory-route-arrow">➜</span>}
                            <span className="advisory-route-step px-1.5 py-0.5 rounded-lg tracking-wider">
                              {step}
                            </span>
                          </React.Fragment>
                        ))}
                      </div>
                    )}

                    <div className="advisory-response text-xs leading-relaxed font-medium space-y-3 select-text flex-1" aria-live="polite">
                      {explanationText.startsWith("[INIT]") ? (
                        /* Premium Dynamic Terminal Readout - Real-time and Customized! */
                        <div className="advisory-empty-state text-sm space-y-3 text-left p-5 rounded-2xl">
                          <p className="font-bold text-base">Hello {farmerProfile.farmer_name}, how can we help?</p>
                          <p className="text-zinc-600 leading-relaxed">Ask a question in your language, upload a clear leaf photo, or check today&apos;s farm conditions.</p>
                          <div className="text-zinc-600 leading-relaxed space-y-1.5">
                            <div>• Speak or type: “Why are my leaves turning yellow?”</div>
                            <div>• For a photo, use a well-lit leaf with the spots visible.</div>
                            <div>• Use the advice as a guide and contact a local expert for urgent problems.</div>
                          </div>
                        </div>
                      ) : (
                        explanationText.split('\n\n').map((paragraph, pIdx) => {
                          if (paragraph.startsWith('-')) {
                            return (
                              <ul key={pIdx} className="advisory-bullet-group list-disc list-inside space-y-1 p-2.5 rounded-2xl font-mono text-[9.5px]">
                                {paragraph.split('\n').map((bullet, bIdx) => (
                                  <li key={bIdx} className="advisory-bullet pl-1 font-semibold leading-relaxed list-none text-[9.5px]">
                                    <span className="mr-1.5 font-bold">•</span>
                                    {bullet.replace('- ', '').split('**').map((text, i) => (
                                      i % 2 === 1 ? <strong key={i} className="font-extrabold">{text}</strong> : text
                                    ))}
                                  </li>
                                ))}
                              </ul>
                            );
                          }
                          
                          return (
                            <p key={pIdx} className="advisory-paragraph font-semibold whitespace-pre-line leading-relaxed text-[10.5px]">
                              {paragraph.split('**').map((text, i) => (
                                i % 2 === 1 ? <strong key={i} className="font-black">{text}</strong> : text
                              ))}
                            </p>
                          );
                        })
                      )}
                      {isTypingAdvice && <span className="advisory-caret" aria-hidden="true">▋</span>}

                    {/* If we have structured agentOutput, show a high-tech detailed diagnostic summary grid! */}
                    {agentOutput && !explanationText.startsWith("[INIT]") && (
                      <div className="advisory-diagnostics border-t pt-3 mt-3 space-y-2 font-mono">
                        <div className="advisory-diagnostics-label text-[9px] font-bold uppercase tracking-wider flex items-center gap-1 select-none">
                          <Sparkles size={11} className="animate-spin" />
                          <span>Multi-Agent Diagnostics Breakdown</span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[9.5px]">
                          {/* Vision Analysis Block */}
                          {agentOutput.vision_results && (
                              <div className="advisory-agent-card advisory-agent-card--vision p-2.5 rounded-2xl">
                               <span className="font-bold block mb-1">VISION_AGENT</span>
                               <div className="space-y-0.5">
                                 <div>Target: <span className="font-semibold">{agentOutput.vision_results.target}</span></div>
                                 <div>Pathogen: <span className="font-semibold text-[8.5px]">{agentOutput.vision_results.disease}</span></div>
                                <div>Confidence: <span className="text-emerald-400">{(agentOutput.vision_results.confidence * 100).toFixed(0)}%</span></div>
                              </div>
                            </div>
                          )}

                          {/* Weather Analysis Block */}
                          {agentOutput.weather_info && (
                             <div className="advisory-agent-card advisory-agent-card--weather p-2.5 rounded-2xl">
                               <span className="font-bold block mb-1">METEOROLOGICAL_AGENT</span>
                               <div className="space-y-0.5">
                                 <div>Temperature: <span className="font-semibold">{agentOutput.weather_info.temperature}°C</span></div>
                                 <div>Humidity: <span className="font-semibold">{agentOutput.weather_info.humidity}%</span></div>
                                <div className="truncate text-amber-400 text-[8.5px]" title={agentOutput.weather_info.advisory}>Advisory: {agentOutput.weather_info.advisory}</div>
                              </div>
                            </div>
                          )}

                          {/* Soil Analysis Block */}
                          {agentOutput.soil_data && (
                             <div className="advisory-agent-card advisory-agent-card--soil p-2.5 rounded-2xl">
                               <span className="font-bold block mb-1">TELEMETRY_SOIL_AGENT</span>
                               <div className="space-y-0.5">
                                 <div>Soil Type: <span className="font-semibold">{agentOutput.soil_data.soil_type}</span></div>
                                 <div>pH Value: <span className="font-semibold">{agentOutput.soil_data.ph}</span></div>
                                <div className="text-[8px] text-zinc-300 font-semibold">NPK: {agentOutput.soil_data.nitrogen}N : {agentOutput.soil_data.phosphorus}P : {agentOutput.soil_data.potassium}K</div>
                              </div>
                            </div>
                          )}

                          {/* Mandi/Market Rates Block */}
                          {agentOutput.market_rates && (
                             <div className="advisory-agent-card advisory-agent-card--market p-2.5 rounded-2xl">
                               <span className="font-bold block mb-1">MANDI_MARKET_AGENT</span>
                               <div className="space-y-0.5">
                                 <div className="truncate">Mandi: <span className="font-semibold text-[8.5px]">{agentOutput.market_rates.mandi}</span></div>
                                 <div>Price: <span className="font-semibold">₹{agentOutput.market_rates.price}/q</span></div>
                                <div className="text-amber-400 text-[8.5px] truncate font-semibold" title={agentOutput.market_rates.best_time}>Trend: {agentOutput.market_rates.best_time}</div>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                  <div className="advisory-note rounded-lg p-3 text-xs font-semibold mt-3 shrink-0 text-left">
                   <span>Advice is based on your crop, location, soil and weather data.</span>
              </div>
            </div>
          </div>
        </div>
          )}

          {/* TAB 3: MARKET & MANDI */}
          {activeTab === "market" && (
            <div className="h-full min-h-0 overflow-y-auto pb-4">
              <Marketprice 
                marketRates={agentOutput?.market_rates}
                activeLanguage={activeLanguage}
              />
            </div>
          )}

          {/* TAB 4: CRISIS & ACADEMY */}
          {activeTab === "crisis" && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start pb-8">
              {/* Emergency SOS Mitigation Console */}
              <div className="lg:col-span-5 w-full">
                <EmergencySOS 
                  medicalAdvice={agentOutput?.medical_advice}
                  disasterAlerts={agentOutput?.disaster_alerts}
                  activeLanguage={activeLanguage}
                />
              </div>

              {/* Krishi Academy Education Portal */}
              <div className="lg:col-span-7 w-full">
                <EducationPortal 
                  tutorials={agentOutput?.tutorials || []}
                  quizQuestions={agentOutput?.quiz_questions}
                  activeLanguage={activeLanguage}
                />
              </div>
            </div>
          )}

        </div>

        </main>

        {/* Footer (Floating Capsule Design) */}
        <footer className="farmer-panel mx-4 mb-4 mt-6 p-4 bg-white/90 border border-emerald-900/10 rounded-2xl shrink-0 flex flex-col md:flex-row justify-between items-center gap-4 backdrop-blur-md text-xs text-zinc-450 select-none shadow-[0_0_20px_rgba(32,79,51,0.08)] relative z-10 text-left">
          <div className="flex flex-wrap items-center justify-center gap-3">
            <span className="flex items-center gap-1.5 text-emerald-450 font-bold bg-emerald-950/45 px-2.5 py-1 rounded-xl border border-emerald-500/10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
               Connection ready
            </span>
            <span className="flex items-center gap-1.5 text-cyan-400 font-bold bg-cyan-950/45 px-2.5 py-1 rounded-xl border border-cyan-500/10">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
               Live farm data
            </span>
            <span className="flex items-center gap-1.5 text-fuchsia-400 font-bold bg-fuchsia-950/45 px-2.5 py-1 rounded-xl border border-fuchsia-500/10">
              <span className="w-1.5 h-1.5 rounded-full bg-fuchsia-400 animate-pulse"></span>
               Your data is private
            </span>
          </div>
          <div className="flex flex-col md:flex-row items-center gap-2 md:gap-4 text-center md:text-right">
            <span className="text-zinc-500">© 2026 Agriva </span>
            <span className="text-emerald-400 font-extrabold uppercase bg-black/60 px-2 py-0.5 rounded border border-white/5">
               Agriva farm assistant
            </span>
          </div>
        </footer>

      </div>


      {/* Dynamic HUD Help Information overlay popup */}
      {activeInfoTopic && (
        <div 
          className="fixed inset-0 z-[99999] bg-black/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in"
          onClick={() => setActiveInfoTopic(null)}
        >
          <div 
            className="relative bg-[#050806] border border-emerald-500/20 shadow-[0_0_60px_rgba(16,185,129,0.25)] rounded-3xl p-6 max-w-sm w-full text-left animate-scale-up select-none overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Corner cyber bracket overlays */}
            <div className="absolute top-0 left-0 w-6 h-6 border-t-2 border-l-2 border-emerald-500/30 rounded-tl-3xl pointer-events-none" />
            <div className="absolute top-0 right-0 w-6 h-6 border-t-2 border-r-2 border-emerald-500/30 rounded-tr-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-6 h-6 border-b-2 border-l-2 border-emerald-500/30 rounded-bl-3xl pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-6 h-6 border-b-2 border-r-2 border-emerald-500/30 rounded-br-3xl pointer-events-none" />

            <div className="flex justify-between items-center border-b border-white/10 pb-3 mb-4">
              <h3 className="text-sm font-black text-white tracking-wide uppercase flex items-center gap-1.5">
                <Info size={14} className="text-emerald-400" />
                {activeInfoTopic.title}
              </h3>
              <button 
                onClick={() => setActiveInfoTopic(null)}
                className="p-1 rounded-lg bg-emerald-950/60 border border-emerald-500/15 text-emerald-450 hover:text-white transition-all cursor-pointer"
              >
                <X size={12} />
              </button>
            </div>

            <p className="text-xs leading-relaxed text-zinc-350 bg-black/40 p-4 rounded-xl border border-white/5 font-medium italic">
              {activeInfoTopic.desc}
            </p>

            <div className="mt-5 flex justify-end">
              <button 
                onClick={() => setActiveInfoTopic(null)}
                className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-black text-[10px] font-black rounded-lg uppercase tracking-wider transition-colors cursor-pointer"
              >
                Close HUD
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Dynamic Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-8 right-8 z-[9999] bg-[#090f0c]/90 backdrop-blur-lg border border-emerald-500 text-emerald-450 font-mono text-[10px] font-bold px-4 py-2.5 rounded-full shadow-[0_0_20px_rgba(16,185,129,0.35)] flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-450 animate-ping"></span>
          {toastMessage}
        </div>
      )}

    </div>
  );
}
