import InfoTooltip from "./InfoToolTip";
import CrowdBadges from "./CrowdBadges";
import EnvironmentPanel from "./EnvironmentalPanel";

export default function WellbeingMeter({ wellbeing, crowd, env }) {
  return (
    <InfoTooltip text="Combines emotional, environmental, and crowd-based data to estimate overall public wellbeing.">
      <div className="bg-gray-800 p-4 rounded-xl">
        <div className="flex justify-between items-center">
          <h3 className="text-lg text-white font-semibold">Public Wellbeing Meter</h3>
          <div className="text-sm text-blue-200">Score: {wellbeing}</div>
        </div>

        <div className="w-full bg-red-900/30 h-4 rounded-full mt-2">
          <div
            className="h-4 rounded-full"
            style={{
              width: `${wellbeing}%`,
              backgroundColor: wellbeing > 70 ? "green" : wellbeing > 40 ? "yellow" : "red",
            }}
          ></div>
        </div>

        <CrowdBadges crowd={crowd} />

        <div className="mt-4">
          <div className="text-white font-semibold mb-2">Environment Details</div>
          <EnvironmentPanel env={env} />
        </div>
      </div>
    </InfoTooltip>
  );
}
