import os
import glob
import datetime

# Set project root to current working directory
PROJECT_ROOT = os.getcwd()
OUTPUT_FILE = "ckicas-complete-snapshot.txt"

# Explicitly requested files in order
files_to_check = [
    "package.json",
    "vite.config.ts",
    "tsconfig.json",
    "index.html",
    "index.tsx",
    "index.css",
    "App.tsx",
    "constants.ts",
    "types.ts",
    "services/api.ts",
    "components/DroughtMap.tsx",
    "components/ChatInterface.tsx",
    "components/HistoricalChart.tsx",
    "components/StatusCard.tsx",
    "components/QuickStats.tsx",
    "components/RegionSearch.tsx",
    "components/DataRefreshIndicator.tsx",
    "components/CouncilAlerts.tsx",
    "components/NewsTicker.tsx",
    "components/WeatherNarrative.tsx",
    "components/ShortcutsHelpModal.tsx",
    "components/QuickStatsSkeleton.tsx",
    "components/WeatherMetricsSkeleton.tsx",
    "components/HistoricalChartSkeleton.tsx",
    "pages/Triggers.tsx",
    "pages/SystemDynamics.tsx",
    "hooks/useKeyboardShortcuts.ts",
    "utils/toast.ts"
]

# Patterns to catch any other files
patterns = [
    "components/*.tsx",
    "pages/*.tsx",
    "hooks/*.ts",
    "utils/*.ts"
]

# Collect all files
final_file_list = []
seen_files = set()

# Add explicit files first
for f in files_to_check:
    # Normalize path separators
    norm_path = f.replace("/", os.sep).replace("\\", os.sep)
    if norm_path not in seen_files:
        final_file_list.append(norm_path)
        seen_files.add(norm_path)

# Add globbed files
for pattern in patterns:
    # glob returns paths relative to CWD usually
    for filepath in glob.glob(pattern):
        norm_path = filepath.replace("/", os.sep).replace("\\", os.sep)
        if norm_path not in seen_files:
            final_file_list.append(norm_path)
            seen_files.add(norm_path)

# Write the snapshot
with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
    # Header
    outfile.write(f"PROJECT: CKICAS Drought Monitor\n")
    outfile.write(f"PURPOSE: Performance diagnosis for slow loading issue\n")
    outfile.write(f"DATE: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    outfile.write(f"PROJECT ROOT: {PROJECT_ROOT}\n\n")

    count = 0
    skipped = []

    for file_path in final_file_list:
        full_path = os.path.join(PROJECT_ROOT, file_path)
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            outfile.write("=" * 80 + "\n")
            # Use forward slashes for display in the text file
            display_path = file_path.replace(os.sep, "/")
            outfile.write(f"FILE: {display_path}\n")
            outfile.write("=" * 80 + "\n")
            try:
                with open(full_path, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())
            except Exception as e:
                outfile.write(f"[Error reading file: {e}]")
            outfile.write("\n\n")
            count += 1
        else:
            # Check if it was one of the explicitly requested ones
            # We need to check against the original list which might use forward slashes
            # Convert file_path back to forward slash for comparison
            forward_slash_path = file_path.replace(os.sep, "/")
            if forward_slash_path in files_to_check:
                skipped.append(forward_slash_path)

    outfile.write("=" * 80 + "\n")
    outfile.write("END OF SNAPSHOT\n")
    outfile.write(f"Total Files: {count}\n")
    outfile.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if skipped:
        outfile.write("Skipped Files (Not Found):\n")
        for s in skipped:
            outfile.write(f"- {s}\n")
            
    outfile.write("=" * 80 + "\n")

print(f"Snapshot generated at {os.path.join(PROJECT_ROOT, OUTPUT_FILE)}")
