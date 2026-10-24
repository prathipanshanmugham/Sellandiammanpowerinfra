import { useSyncExternalStore } from "react";
import { store } from "./api";

// English / Tamil for the website's navigation, buttons and form labels. Page content from the editor stays as written.
const TA = {
  "Services": "சேவைகள்", "Projects": "திட்டங்கள்", "Industries": "தொழில்கள்", "Tools": "கணக்கீட்டு கருவிகள்", "About": "எங்களைப் பற்றி",
  "Contact": "தொடர்பு", "Get a quote": "விலைப்புள்ளி பெறுக", "Book a site survey": "தள ஆய்வு முன்பதிவு", "Client login": "வாடிக்கையாளர் உள்நுழைவு",
  "Call us": "அழையுங்கள்", "WhatsApp us": "வாட்ஸ்அப்", "Products": "பொருட்கள்", "Clients": "வாடிக்கையாளர்கள்", "Gallery": "படங்கள்",
  "Resources": "வழிகாட்டிகள்", "Careers": "வேலைவாய்ப்பு", "Emergency": "அவசர சேவை", "AMC & maintenance": "பராமரிப்பு ஒப்பந்தம்",
  "Your name": "உங்கள் பெயர்", "Mobile number": "கைபேசி எண்", "Email (optional)": "மின்னஞ்சல் (விருப்பம்)", "Company": "நிறுவனம்",
  "Town": "ஊர்", "Message": "செய்தி", "Send enquiry": "விசாரணை அனுப்பு", "Request a call back": "திரும்ப அழைக்கவும்",
  "Next": "அடுத்து", "Back": "பின்", "Thank you": "நன்றி", "Safety & quality": "பாதுகாப்பு & தரம்", "Invite us to bid": "டெண்டருக்கு அழைக்கவும்",
  "24×7 breakdown": "24×7 பழுது சேவை", "Staff login": "பணியாளர் உள்நுழைவு", "Privacy": "தனியுரிமை", "Terms": "விதிமுறைகள்",
  "Vendor registration": "விற்பனையாளர் பதிவு", "Free bill review": "இலவச மின்கட்டண ஆய்வு", "All services": "அனைத்து சேவைகள்",
  "See all projects": "அனைத்து திட்டங்களும்", "Open the calculator": "கணக்கிடு", "Calculate": "கணக்கிடு",
};
let lang = store.get("spi_lang", "en");
const ls = new Set();
export const setLang = (l) => { lang = l; store.set("spi_lang", l); document.documentElement.lang = l === "ta" ? "ta" : "en"; ls.forEach((f) => f()); };
export function useLang() { return useSyncExternalStore((cb) => { ls.add(cb); return () => ls.delete(cb); }, () => lang, () => lang); }
export function useT() {
  const l = useLang();
  return (s) => (l === "ta" && TA[s]) || s;
}
