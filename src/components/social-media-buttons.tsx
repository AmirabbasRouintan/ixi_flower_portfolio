"use client";

import { cn } from "@/lib/utils";
import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  className?: string;
  children: React.ReactNode;
}

const StaticButton = ({ className, children, ...props }: ButtonProps) => {
  return (
    <button
      className={cn(
        "flex min-w-[120px] cursor-pointer items-center justify-center gap-2 rounded-full bg-green-500 px-4 py-2 font-medium text-white ring-offset-2 transition duration-200 hover:ring-2 hover:ring-green-500 dark:ring-offset-black",
        className,
      )}
      {...props}
    >
      <span>{children}</span>
    </button>
  );
};

export function SocialMediaButtons() {
  const socialLinks = {
    linkedin: "https://www.linkedin.com/in/amirabbas-rouintan/",
    github: "https://github.com/AmirabbasRouintan",
    youtube: "https://www.youtube.com/@ixi_flower"
  };

  const handleLinkedInClick = () => {
    window.open(socialLinks.linkedin, "_blank");
  };

  const handleGitHubClick = () => {
    window.open(socialLinks.github, "_blank");
  };

  const handleYouTubeClick = () => {
    window.open(socialLinks.youtube, "_blank");
  };

  return (
    <div className="flex flex-wrap gap-4 justify-center items-center p-6">
      <StaticButton 
        onClick={handleLinkedInClick}
        className="bg-blue-700 hover:bg-white hover:text-blue-700"
      >
        LinkedIn
      </StaticButton>
      <StaticButton 
        onClick={handleGitHubClick}
        className="bg-gray-900 hover:bg-white hover:text-gray-900"
      >
        GitHub
      </StaticButton>
      <StaticButton 
        onClick={handleYouTubeClick}
        className="bg-red-600 hover:bg-white hover:text-red-600"
      >
        YouTube
      </StaticButton>
    </div>
  );
}