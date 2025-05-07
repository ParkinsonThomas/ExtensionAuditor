import json
import importlib
import time

def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file)
    
def run_module(module_name, config):
    #try:
        module = importlib.import_module(module_name)

        if hasattr(module, "main"):
            print("")
            print(f"Running {module_name}...")
            module.main(config)
        else:
            print("")
            print(f"ERROR! Skipping module {module_name} - No main() function found.")
    
    #except ModuleNotFoundError:
    #    print("")
    #    print(f"ERROR! Skipping module {module_name} - Module not found.")
    #except Exception as e:
    #    print("")
    #    print(f"ERROR! Skipping {module_name} - {e}")

def main():
    # Start time
    start_time = time.time()
    config = load_config()
    print("Config loaded.")

    for module in config.get("modules", []):
        if module.get("enabled", False):
            run_module(module["name"], config)

    # Formats and outputs execution time
    end_time = time.time()
    elapsed_time = end_time - start_time

    hours = int(elapsed_time // 3600)
    minutes = int((elapsed_time % 3600) // 60)
    seconds = int(elapsed_time % 60)

    print(f"Total execution time: {hours:02d}hrs, {minutes:02d}mins, {seconds:02d}secs")

if __name__ == "__main__":
    main()