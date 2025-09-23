import { Linkedin, Youtube, Instagram, Send, Github } from "lucide-react";
import ShinyText from "./ShinyText";
import CountUp from "./CountUp";
import God5 from "../assets/god5.svg";
import MobileFooter from "../assets/mobile/mobile_footer.svg";
import { useEffect, useState } from "react";
import { useViewCounter } from "../hooks/useViewCounter";

const PageFooter: React.FC = () => {
  const [isMobile, setIsMobile] = useState(false);
  // Use the view counter hook to get and increment the view count
  const viewCount = useViewCounter();

  useEffect(() => {
    // Check if screen width is mobile size
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    // Initial check
    checkMobile();
    
    // Add event listener for window resize
    window.addEventListener('resize', checkMobile);
    
    // Cleanup
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  return (
    <>
      <footer className="relative w-full h-screen pt-20 pb-8 sm:mt-20">
        <div 
          className="absolute inset-0"
          style={{
            backgroundImage: `url(${isMobile ? MobileFooter : God5})`,
            backgroundSize: isMobile ? "150%" : "cover",
            backgroundPosition: isMobile ? "center bottom" : "center",
            backgroundRepeat: "no-repeat",
            opacity: 0.5
          }}
        />
        <div className="relative h-full flex flex-col justify-end items-center pb-32">
          <div
            className="grid grid-cols-3 gap-8 max-w-[1200px] mx-auto mb-20"
          >
            <div className="text-center">
              <CountUp 
                from={0} 
                to={viewCount} 
                separator="," 
                direction="up" 
                duration={1}
                useShiny={true}
                shinySpeed={3}
                className={`${isMobile ? 'text-5xl' : 'text-7xl'} font-bold text-white`}
              />
              <ShinyText
                text="viewers"
                disabled={false}
                speed={3}
                className="text-white mt-2 text-xs"
              />
            </div>
            
            <div className="text-center">
              <CountUp 
                from={0} 
                to={37} 
                separator="," 
                direction="up" 
                duration={1}
                useShiny={true}
                shinySpeed={3}
                className={`${isMobile ? 'text-5xl' : 'text-7xl'} font-bold text-white`}
              />
              <ShinyText
                text="GitHub Repositories"
                disabled={false}
                speed={3}
                className="text-white mt-2 text-xs"
              />
            </div>
            
            <div className="text-center">
              <CountUp 
                from={0} 
                to={5} 
                separator="," 
                direction="up" 
                duration={1}
                useShiny={true}
                shinySpeed={2}
                className={`${isMobile ? 'text-5xl' : 'text-7xl'} font-bold text-white`}
              />
              <ShinyText
                text="Years Learning"
                disabled={false}
                speed={3}
                className="text-white mt-2 text-xs"
              />
            </div>
          </div>

          <div className="absolute bottom-0 w-full flex flex-col sm:flex-row justify-between items-center px-4 sm:px-8 py-4 gap-2">
            <div className="flex gap-4">
              <Send size={24} color="#878787" />
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Github size={24} color="#878787" />
              </a>
              <Instagram size={24} color="#878787" />
              <Youtube size={24} color="#878787" />
              <Linkedin size={24} color="#878787" />
            </div>
            <div style={{ color: "#878787" }}>
              <ShinyText
                text="© Developer Portfolio by ixi_flower"
                disabled={false}
                speed={3}
                className="custom-class text-center mx-auto"
              />
            </div>
          </div>
        </div>
      </footer>
    </>
  );
};

export default PageFooter;