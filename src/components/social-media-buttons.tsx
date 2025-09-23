"use client";

import React from "react";
import { Button } from "@/components/ui/stateful-button";

export function SocialMediaButtons() {
  // Social media URLs
  const socialLinks = {
    linkedin: "https://www.linkedin.com/in/amirabbas-rouintan/",
    github: "https://github.com/AmirabbasRouintan",
    youtube: "https://www.youtube.com/@ixi_flower"
  };

  // Functions to handle button clicks with navigation
  const handleLinkedInClick = () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        window.open(socialLinks.linkedin, "_blank");
        resolve();
      }, 2000);
    });
  };

  const handleGitHubClick = () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        window.open(socialLinks.github, "_blank");
        resolve();
      }, 2000);
    });
  };

  const handleYouTubeClick = () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        window.open(socialLinks.youtube, "_blank");
        resolve();
      }, 2000);
    });
  };

  return (
    <div className="flex flex-wrap gap-4 justify-center items-center p-6">
      <Button 
        onClick={handleLinkedInClick}
        className="bg-blue-700 hover:bg-white hover:text-blue-700"
      >
        LinkedIn
      </Button>
      <Button 
        onClick={handleGitHubClick}
        className="bg-gray-900 hover:bg-white hover:text-gray-900"
      >
        GitHub
      </Button>
      <Button 
        onClick={handleYouTubeClick}
        className="bg-red-600 hover:bg-white hover:text-red-600"
      >
        YouTube
      </Button>
    </div>
  );
}