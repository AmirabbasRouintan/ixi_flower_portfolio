// Import all assets
import God1 from "../assets/god1.svg";
import God2 from "../assets/god2.svg";
import God3 from "../assets/God3.svg";
import God4 from "../assets/god4.svg";
import Bg1 from "../assets/bg1.svg";
import thunder1 from "../assets/thunder.svg";
import bg_video from "../assets/bg_video.png";
import david from "../assets/david.png";
import video1 from "../assets/video1.gif";

// Grid images import
import gridImg1 from "../assets/grid/img1.png";
import gridImg2 from "../assets/grid/img2.png";
import gridImg3 from "../assets/grid/img3.png";
import gridImg4 from "../assets/grid/img4.png";
import gridImg5 from "../assets/grid/img5.png";
import gridImg6 from "../assets/grid/img6.png";
import gridImg7 from "../assets/grid/img7.png";
import gridImg8 from "../assets/grid/img8.png";
import gridImg9 from "../assets/grid/img9.png";
import gridImg10 from "../assets/grid/img10.png";

// Import icons
import {
  Terminal,
  Code,
  Atom,
  Smartphone,
  Database,
  Server,
  Globe,
  Shield,
  Container,
  Layers,
  FileCode,
  Lock,
} from "lucide-react";

// Courses data
export const courses = [
  {
    id: 1,
    title: "CompTIA Network+",
    description: "Arjang Institute of Higher Education",
    image:
      "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxARDxESERAQFRAQEBUWGBIWGRgWFhgTGhcYGhoXGRkdHSkgHRoxIBgZLTIiJSksLi8uGx8zODMtNygtLisBCgoKDg0OGxAQGjclHiUrKy0rLSsuNy0tNystKystLTgrLTA4Ny0tLTcrLS0tLS0tLS0rLS0tMC03NzctKysrLf/AABEIAMgAyAMBIgACEQEDEQH/xAAcAAEAAwADAQEAAAAAAAAAAAAABQYHAgMECA...",
  },
  {
    id: 2,
    title: "security plus",
    description: "Maktabkhoonehs",
    image:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAA0lBMVEUBm6f///8Bmqj///0Ak57//v+y2uADmqYAl6U8qrRFqrQAlKEEl6JftL3h8fAAkZ+h0tbq9/bz+/sAnKW85ucDmalKq7D8//sAlJ3//fwAjp0Aj5sAlKYAjZ4Al5+43+GNy9AAnaJ1vcGWytEAl6wAk6nF4+YAiZip2OC43eaDxMgkoqnS7u2z3+JIqbZsvL5JqqqCvMeo0NPg8u7J4uij19h...",
  },
  {
    id: 3,
    title: "Udemy - nmap",
    description: "The Complete Nmap Ethical Hacking Course : Network Security",
    image:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAyVBMVEX///8AAACkNvEoKCh3d3f///0TExP+/f+xVPOlNfGiMfD9//////v///r9//3//f26urpZWVmtra3W1tY0NDT4+PikNu7j4+ORkZGuUPPeuPyhLPCfG+2cHu/69P7Sofo8PDyBgYHNzc2VlZVTU1Pv7+9ubm6jo6PCwsLv4/vy3/q5aPOcAezIi/T87/3drfvoyvjAcvLNkvKvWe/q1fnCe/P...",
  },
  {
    id: 4,
    title: "Certified Ethical Hacker (CEH) Training",
    description: "Maktabkhooneh - Jadi",
    image:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAA0lBMVEUBm6f///8Bmqj///0Ak57//v+y2uADmqYAl6U8qrRFqrQAlKEEl6JftL3h8fAAkZ+h0tbq9/bz+/sAnKW85ucDmalKq7D8//sAlJ3//fwAjp0Aj5sAlKYAjZ4Al5+43+GNy9AAnaJ1vcGWytEAl6wAk6nF4+YAiZip2OC43eaDxMgkoqnS7u2z3+JIqbZsvL5JqqqCvMeo0NPg8u7J4uij19h...",
  },
  {
    id: 5,
    title: "Kubernetes",
    description: "Youtube - Codecamp",
    image:
      "https://yt3.googleusercontent.com/ytc/AIdro_lGRc-05M2OoE1ejQdxeFhyP7OkJg9h4Y-7CK_5je3QqFI=s160-c-k-c0x00ffffff-no-rj",
  },
  {
    id: 6,
    title: "THE BIGGEST REACT.JS COURSE ON THE INTERNET",
    description: "YouTube",
    image:
      "https://yt3.googleusercontent.com/ojm5jnygbYT1l23g94ovEykcM2NV-wAp-W7dzvWzttqaV1sA8tXj3mwicsVUaJyzhBZ_F-9l=s160-c-k-c0x00ffffff-no-rj",
  },
  {
    id: 7,
    title: "LPIC-1 Bootcamp - Jadi",
    description: "Youtube",
    image:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAwFBMVEX////+ADL9////ABr9x9L8///+ATH+AC/9ATP+AC3+ACb//v3+ACv/ACT+ACn8ATL+ABX+AB//ABH+ADn/8vj/+fz/zNj+g5X+UGv8cYX98vT+pa79JU7/fI//TWb82+L+t8H/srr9nar/k6L+jJz+anz/YXb/WXH/QV7/Mlb9F0b/AD78QmP9an7+1N7+sL/6L1f/AAD+9f78KEf...",
  },
  {
    id: 8,
    title: "The Modern Python - with certification",
    description: "Udemy",
    image:
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAAAyVBMVEX///8AAACkNvEoKCh3d3f///0TExP+/f+xVPOlNfGiMfD9//////v///r9//3//f26urpZWVmtra3W1tY0NDT4+PikNu7j4+ORkZGuUPPeuPyhLPCfG+2cHu/69P7Sofo8PDyBgYHNzc2VlZVTU1Pv7+9ubm6jo6PCwsLv4/vy3/q5aPOcAezIi/T87/3drfvoyvjAcvLNkvKvWe/q1fnCe/P...",
  },
  {
    id: 9,
    title: "The Modern Python",
    description: "Arjang",
    image:
      "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxARDxESERAQFRAQEBUWGBIWGRgWFhgTGhcYGhoXGRkdHSkgHRoxIBgZLTIiJSksLi8uGx8zODMtNygtLisBCgoKDg0OGxAQGjclHiUrKy0rLSsuNy0tNystKystLTgrLTA4Ny0tLTcrLS0tLS0tLS0rLS0tMC03NzctKysrLf/AABEIAMgAyAMBIgACEQEDEQH/xAAcAAEAAwADAQEAAAAAAAAAAAAABQYHAgMECA...",
  },
  {
    id: 10,
    title: "OWASP Zero",
    description: "Voorivex Academy",
    image:
      "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhITEhMWFhUXFhgXFxcYFRoYIBcXGRcaGBgVFhgYHSgiGBsmGxYWITEhJSktLy4vFyA/ODMtNygtLi0BCgoKDg0OGxAQGzAlHyUtLS0wNy83LS0tLS8tLS0tNy0vLy03LTUvLS03Li0tLS8tLS0tLS0tLS8tLy8vKzEtLf/AABEIAOEA4QMBIgACEQEDEQH/xAAcAAEAAQUBAQAAAAAAAAAAAAAABQIDBAYHAQ...",
  },
];

// Export all assets
export {
  God1,
  God2,
  God3,
  God4,
  Bg1,
  thunder1,
  bg_video,
  david,
  video1,
  gridImg1,
  gridImg2,
  gridImg3,
  gridImg4,
  gridImg5,
  gridImg6,
  gridImg7,
  gridImg8,
  gridImg9,
  gridImg10,
};

// Export icons
export {
  Terminal,
  Code,
  Atom,
  Smartphone,
  Database,
  Server,
  Globe,
  Shield,
  Container,
  Layers,
  FileCode,
  Lock,
};