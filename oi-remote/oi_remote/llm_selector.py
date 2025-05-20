import os
# Assuming Open Interpreter's LLM classes are accessible like this:
# Adjust imports based on actual Open Interpreter structure if different.
from openinterpreter.llm.llm import LLM # General LLM interface or specific classes
from openinterpreter.llm.setup_llm import setup_llm # Utility to setup/configure LLM

# Fallback if direct class imports are tricky or subject to change in OI:
# We might need to rely on OI's internal registration or factory methods if they exist.
# For this example, we'll assume direct instantiation or use of setup_llm is possible.

class LLMSelector:
    def __init__(self, interpreter_instance):
        """
        Initializes the LLMSelector.
        Args:
            interpreter_instance: The instance of Open Interpreter's Interpreter class.
                                  This is needed to set its LLM properties.
        """
        self.interpreter = interpreter_instance
        self.provider = os.environ.get("OI_LLM_PROVIDER", "openai").lower()
        self.api_key = os.environ.get("OI_LLM_KEY")
        self.model_name = os.environ.get("OI_LLM_MODEL")
        self.api_base = os.environ.get("OI_LLM_API_BASE") # For OpenAI-compatible APIs like Ollama

        # Validate provider and API key presence (except for Ollama if it runs locally without key)
        supported_providers = ["openai", "anthropic", "ollama"] # Add more as OI supports them
        if self.provider not in supported_providers:
            raise ValueError(f"Unsupported LLM provider: {self.provider}. Supported: {supported_providers}")
        
        if self.provider != "ollama" and not self.api_key:
            print(f"Warning: OI_LLM_KEY not set for provider '{self.provider}'. LLM may not function.")

    def configure_llm(self):
        """Configures the LLM on the interpreter instance based on environment variables."""
        
        # These attributes are commonly found on the Open Interpreter instance
        # and are used by its internal `setup_llm` or similar LLM initialization logic.
        self.interpreter.llm.model = self.model_name if self.model_name else self.interpreter.llm.model
        self.interpreter.llm.api_key = self.api_key if self.api_key else self.interpreter.llm.api_key
        self.interpreter.llm.api_base = self.api_base if self.api_base else self.interpreter.llm.api_base
        
        # Handle provider-specific model naming or settings if needed
        if self.provider == "ollama":
            # OI's Ollama integration might expect model name like "ollama/llama3"
            # Or it might handle the prefix internally when api_base suggests Ollama.
            if self.model_name and not self.model_name.startswith("ollama/"):
                self.interpreter.llm.model = f"ollama/{self.model_name}"
            elif not self.model_name and not self.interpreter.llm.model:
                 self.interpreter.llm.model = f"ollama/llama3" # Default if nothing specified
            self.interpreter.llm.api_key = "ollama" # Often a placeholder for local LLMs
            if not self.interpreter.llm.api_base:
                self.interpreter.llm.api_base = "http://localhost:11434/v1" # Default Ollama API base

        elif self.provider == "openai":
            if not self.interpreter.llm.model: self.interpreter.llm.model = "gpt-4o"
        elif self.provider == "anthropic":
            if not self.interpreter.llm.model: self.interpreter.llm.model = "claude-3-opus-20240229"

        # After setting these, Open Interpreter's internal LLM setup logic needs to be triggered.
        # This might happen automatically if `interpreter.llm` is a property that reconfigures on set,
        # or we might need to call a specific method. The `setup_llm(self.interpreter)` function
        # from OI is a common way to do this.
        try:
            setup_llm(self.interpreter) # This function re-initializes / configures the LLM on the interpreter
            print(f"LLM configured using {self.provider} for model {self.interpreter.llm.model or 'default'}.")
            if self.api_base:
                print(f"Using API base: {self.interpreter.llm.api_base}")
        except Exception as e:
            print(f"Error during LLM setup via setup_llm: {e}")
            print("Please ensure your Open Interpreter version is compatible with this method of LLM configuration.")


def patch_interpreter_llm(interpreter_instance):
    """Call this function after Open Interpreter's Interpreter instance is created."""
    selector = LLMSelector(interpreter_instance)
    selector.configure_llm()
