import oqs
import ipywidgets as widgets
from IPython.display import display, HTML
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

# --- State Management ---
# This dictionary will hold the cryptographic materials,
# removing the need for manual copy-pasting.
_crypto_state = {
    "public_key": None,
    "private_key": None,
    "ciphertext_kem": None,
    "nonce": None,
    "encrypted_message": None,
    "algorithm": None
}

# --- Configuration ---
SUPPORTED_KEMS = ['ML-KEM-512', 'ML-KEM-768', 'ML-KEM-1024']

# --- UI Elements ---

# == Main Header and Algorithm Selection ==
main_header = HTML("<h1>End-to-End PQC Encryption (ML-KEM)</h1>")
main_description = HTML("""
<p>This tool demonstrates a complete hybrid encryption workflow using the Post-Quantum <b>ML-KEM</b> (CRYSTALS-Kyber) algorithm for key exchange and <b>AES-256-GCM</b> for symmetric data encryption.</p>
<p>Follow the steps below from top to bottom. The necessary keys and data will be passed automatically between steps.</p>
""")

kem_dropdown = widgets.Dropdown(
    options=SUPPORTED_KEMS,
    value=SUPPORTED_KEMS[1],
    description='ML-KEM Algorithm:',
    style={'description_width': 'initial'}
)

# == Step 1: Key Generation ==
header_step1 = HTML("<h2>Step 1: Generate Key Pair</h2>")
description_step1 = HTML("<p>First, generate a quantum-resistant public and private key pair for the recipient.</p>")
generate_button = widgets.Button(description='Generate Keys', button_style='success', icon='key')
public_key_output = widgets.Textarea(placeholder='Public Key (Base64) will appear here.', description='Public Key:', layout={'width': '95%', 'height': '100px'}, disabled=True, style={'description_width': 'initial'})
private_key_output = widgets.Textarea(placeholder='Private Key (Base64) will appear here.', description='Private Key:', layout={'width': '95%', 'height': '100px'}, disabled=True, style={'description_width': 'initial'})

# == Step 2: Encryption ==
header_step2 = HTML("<h2>Step 2: Encrypt a Message</h2>")
description_step2 = HTML("<p>Next, as the sender, type a message and encrypt it using the recipient's public key from Step 1.</p>")
message_to_encrypt_input = widgets.Textarea(value='Hello, Post-Quantum World!', placeholder='Type your secret message here.', description='Plaintext Message:', layout={'width': '95%', 'height': '80px'}, disabled=True, style={'description_width': 'initial'})
encrypt_button = widgets.Button(description='Encrypt Message', button_style='primary', icon='lock', disabled=True)
encapsulated_key_output = widgets.Textarea(placeholder='Encapsulated Key (Base64) will appear here.', description='Encapsulated Key:', layout={'width': '95%', 'height': '100px'}, disabled=True, style={'description_width': 'initial'})
nonce_output = widgets.Textarea(placeholder='AES-GCM Nonce (Base64) will appear here.', description='Nonce:', layout={'width': '95%', 'height': '60px'}, disabled=True, style={'description_width': 'initial'})
encrypted_message_output = widgets.Textarea(placeholder='Encrypted Message (Base64) will appear here.', description='Encrypted Message:', layout={'width': '95%', 'height': '100px'}, disabled=True, style={'description_width': 'initial'})

# == Step 3: Decryption ==
header_step3 = HTML("<h2>Step 3: Decrypt the Message</h2>")
description_step3 = HTML("<p>Finally, as the recipient, use your private key from Step 1 to decrypt the message received from the sender in Step 2.</p>")
decrypt_button = widgets.Button(description='Decrypt Message', button_style='success', icon='unlock', disabled=True)
decrypted_message_output = widgets.Textarea(placeholder='Decrypted plaintext will appear here.', description='Decrypted Message:', layout={'width': '95%', 'height': '80px'}, disabled=True, style={'description_width': 'initial'})

# == Status Log ==
status_output = widgets.Output(layout={'width': '95%', 'border': '1px solid #ccc', 'padding': '10px'})

# --- Button Click Handlers ---

def on_generate_button_clicked(b):
    """Handles key generation."""
    with status_output:
        status_output.clear_output()
        print("--- Step 1: Generating Keys ---")

        # Reset state and UI
        for key in _crypto_state: _crypto_state[key] = None
        public_key_output.value = ""
        private_key_output.value = ""
        message_to_encrypt_input.disabled = True
        encrypt_button.disabled = True
        decrypt_button.disabled = True
        decrypted_message_output.value = ""
        
        selected_kem = kem_dropdown.value
        _crypto_state["algorithm"] = selected_kem
        print(f"Using algorithm: {selected_kem}")

        try:
            with oqs.KeyEncapsulation(selected_kem) as kem:
                public_key = kem.generate_keypair()
                secret_key = kem.export_secret_key()
                
                # Store raw bytes in state
                _crypto_state["public_key"] = public_key
                _crypto_state["private_key"] = secret_key
                
                # Display Base64 encoded keys
                public_key_output.value = base64.b64encode(public_key).decode('utf-8')
                private_key_output.value = base64.b64encode(secret_key).decode('utf-8')
                
                print("✅ Key pair generated successfully.")
                print(f"   Public Key Length: {kem.details['length_public_key']} bytes")
                print(f"   Private Key Length: {kem.details['length_secret_key']} bytes")
                
                # Enable next step
                message_to_encrypt_input.disabled = False
                encrypt_button.disabled = False
                print("\nProceed to Step 2 to encrypt a message.")

        except Exception as e:
            print(f"❌ Error during key generation: {e}")

def on_encrypt_button_clicked(b):
    """Handles message encryption."""
    with status_output:
        status_output.clear_output(wait=True) # wait=True helps prevent flickering
        print("--- Step 2: Encrypting Message ---")

        # Reset downstream UI
        decrypt_button.disabled = True
        decrypted_message_output.value = ""
        
        public_key_bytes = _crypto_state.get("public_key")
        plaintext_message = message_to_encrypt_input.value
        
        if not all([public_key_bytes, plaintext_message.strip()]):
            print("❌ Error: Cannot encrypt. Ensure keys are generated and a message is provided.")
            return

        print("1. Encapsulating a shared secret with the public key...")
        try:
            with oqs.KeyEncapsulation(_crypto_state["algorithm"]) as kem:
                ciphertext_kem, shared_secret_kem = kem.encap_secret(public_key_bytes)
                
                _crypto_state["ciphertext_kem"] = ciphertext_kem
                encapsulated_key_output.value = base64.b64encode(ciphertext_kem).decode('utf-8')
                print(f"   ✅ KEM encapsulation successful. Shared secret is {len(shared_secret_kem)} bytes.")

            print("2. Encrypting the message with AES-256-GCM using the shared secret...")
            aes_key = shared_secret_kem
            nonce = os.urandom(12)
            aesgcm = AESGCM(aes_key)
            encrypted_message = aesgcm.encrypt(nonce, plaintext_message.encode('utf-8'), None)
            
            _crypto_state["nonce"] = nonce
            _crypto_state["encrypted_message"] = encrypted_message

            nonce_output.value = base64.b64encode(nonce).decode('utf-8')
            encrypted_message_output.value = base64.b64encode(encrypted_message).decode('utf-8')
            print("   ✅ Symmetric encryption successful.")
            
            # Enable final step
            decrypt_button.disabled = False
            print("\nProceed to Step 3 to decrypt the message.")

        except Exception as e:
            print(f"❌ Error during encryption: {e}")

def on_decrypt_button_clicked(b):
    """Handles message decryption."""
    with status_output:
        status_output.clear_output(wait=True)
        print("--- Step 3: Decrypting Message ---")
        
        decrypted_message_output.value = ""
        
        # Retrieve all necessary components from state
        private_key_bytes = _crypto_state.get("private_key")
        ciphertext_kem_bytes = _crypto_state.get("ciphertext_kem")
        nonce_bytes = _crypto_state.get("nonce")
        encrypted_message_bytes = _crypto_state.get("encrypted_message")
        
        if not all([private_key_bytes, ciphertext_kem_bytes, nonce_bytes, encrypted_message_bytes]):
            print("❌ Error: Cannot decrypt. Missing data from a previous step.")
            return

        print("1. Decapsulating the shared secret with the private key...")
        try:
            with oqs.KeyEncapsulation(_crypto_state["algorithm"], private_key_bytes) as kem:
                shared_secret_kem = kem.decap_secret(ciphertext_kem_bytes)
                print(f"   ✅ KEM decapsulation successful. Recovered shared secret.")

            print("2. Decrypting the message with AES-256-GCM...")
            aesgcm = AESGCM(shared_secret_kem)
            decrypted_payload_bytes = aesgcm.decrypt(nonce_bytes, encrypted_message_bytes, None)
            decrypted_message = decrypted_payload_bytes.decode('utf-8')
            
            decrypted_message_output.value = decrypted_message
            print("   ✅ Symmetric decryption successful.")
            print("\n🎉 Decryption Complete! The original message is displayed above.")
            
        except Exception as e:
            decrypted_message_output.value = "DECRYPTION FAILED. Check logs."
            print(f"❌ Error during decryption: {e}")
            print("   This may happen if the private key does not match the public key used for encapsulation, or if the data was corrupted.")

# --- Link Buttons to Handlers ---
generate_button.on_click(on_generate_button_clicked)
encrypt_button.on_click(on_encrypt_button_clicked)
decrypt_button.on_click(on_decrypt_button_clicked)

# --- Assemble and Display the Full UI ---
full_ui = widgets.VBox([
    main_header,
    main_description,
    kem_dropdown,
    HTML("<hr>"),
    header_step1,
    description_step1,
    generate_button,
    public_key_output,
    private_key_output,
    HTML("<hr>"),
    header_step2,
    description_step2,
    message_to_encrypt_input,
    encrypt_button,
    encapsulated_key_output,
    nonce_output,
    encrypted_message_output,
    HTML("<hr>"),
    header_step3,
    description_step3,
    decrypt_button,
    decrypted_message_output,
    HTML("<hr><h3>Status Log</h3>"),
    status_output
], layout={'width': '100%'})

display(full_ui)