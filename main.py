import json
import importlib

def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file)
    
def run_module(module_name, config):
    try:
        module = importlib.import_module(module_name)

        if hasattr(module, "main"):
            print("")
            print(f"Running {module_name}...")
            module.main(config)
        else:
            print("")
            print(f"ERROR! Skipping module {module_name} - No main() function found.")
    
    except ModuleNotFoundError:
        print("")
        print(f"ERROR! Skipping module {module_name} - Module not found.")
    except Exception as e:
        print("")
        print(f"ERROR! Skipping {module_name} - {e}")

def main():
    config = load_config()
    print("Config loaded.")

    for module in config.get("modules", []):
        if module.get("enabled", False):
            run_module(module["name"], config)

if __name__ == "__main__":
    main()