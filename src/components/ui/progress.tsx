import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"

import { cn } from "@/lib/utils"

function Progress({
  className,
  value,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root>) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn(
        "bg-gray-800 relative h-2 w-full overflow-hidden rounded-full",
        className
      )}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        className="bg-white h-full w-full flex-1 transition-all ease-in-out"
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  )
}

interface ProgressBarProps {
  labelPosition?: "left" | "right" | "top" | "bottom";
  min?: number;
  max?: number;
  value?: number;
  label?: string;
  showValue?: boolean;
}

const ProgressBarTextRight = ({ 
  labelPosition = "left", 
  min = 0, 
  max = 100, 
  value = 0,
  label,
  showValue = true
}: ProgressBarProps) => {
  const percentage = Math.round(((value - min) / (max - min)) * 100);
  
  return (
    <div className="w-full">
      <div className="flex justify-between items-center mb-1">
        {labelPosition === "left" && label && (
          <span className="text-base font-medium text-white">{label}</span>
        )}
        {labelPosition === "right" && (
          <span className="text-base font-medium text-white">{label}</span>
        )}
        {showValue && (
          <span className="text-sm font-medium text-white">{percentage}%</span>
        )}
      </div>
      <Progress value={percentage} className="h-2 bg-gray-800 [&>div]:bg-white" />
    </div>
  );
};

export { Progress, ProgressBarTextRight }
