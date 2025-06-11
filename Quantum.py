from flask import Flask, render_template, request, redirect, url_for, session, flash
import numpy as np
from qutip import basis, Qobj
import PyPDF2
import random
import io

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Constants
NUM_QUBITS = 100  # Number of qubits to transmit
QBER_THRESHOLD = 11  # QBER threshold percentage

# In-memory storage for uploaded and received files
uploaded_files = {}
received_files = {}

# Define the Hadamard gate manually
def hadamard_transform():
    return Qobj([[1, 1], [1, -1]]) / np.sqrt(2)

# Step 1: Generate random bits and bases
def generate_random_bits(num_qubits):
    return np.random.randint(0, 2, num_qubits)

def generate_random_bases(num_qubits):
    return np.random.randint(0, 2, num_qubits)

# Step 2: Prepare qubits
def prepare_qubits(bits, bases):
    qubits = []
    H = hadamard_transform()
    for i in range(len(bits)):
        if bases[i] == 0:  # Z-basis
            qubits.append(basis(2, bits[i]))
        else:  # X-basis
            qubit = H * basis(2, bits[i])
            qubits.append(qubit)
    return qubits

# Step 3: Measure qubits
def measure_qubits(qubits, bases):
    measured_bits = []
    for i in range(len(qubits)):
        if bases[i] == 0:  # Z-basis measurement
            prob_0 = np.abs((basis(2, 0).dag() * qubits[i]))**2
            prob_1 = np.abs((basis(2, 1).dag() * qubits[i]))**2
        else:  # X-basis measurement
            ket_plus = (basis(2, 0) + basis(2, 1)).unit()
            ket_minus = (basis(2, 0) - basis(2, 1)).unit()
            prob_0 = np.abs((ket_plus.dag() * qubits[i]))**2
            prob_1 = np.abs((ket_minus.dag() * qubits[i]))**2
        # Ensure probabilities are real numbers
        prob_0 = prob_0.real
        prob_1 = prob_1.real
        # Normalize probabilities
        total_prob = prob_0 + prob_1
        if total_prob != 0:
            prob_0 /= total_prob
            prob_1 /= total_prob
        else:
            prob_0 = prob_1 = 0.5
        # Clip probabilities to [0, 1]
        prob_0 = np.clip(prob_0, 0, 1)
        prob_1 = np.clip(prob_1, 0, 1)
        # Randomly choose measurement outcome
        measured_bit = np.random.choice([0, 1], p=[prob_0, prob_1])
        measured_bits.append(measured_bit)
    return measured_bits

# Step 4: Compare bases
def compare_bases(alice_bases, bob_bases):
    return [i for i in range(len(alice_bases)) if alice_bases[i] == bob_bases[i]]

# Step 5: Sift key
def sift_key(bits, indices):
    return [bits[i] for i in indices]

# Step 6: Calculate QBER
def calculate_qber(alice_key, bob_key):
    errors = sum(1 for a, b in zip(alice_key, bob_key) if a != b)
    return (errors / len(alice_key)) * 100 if len(alice_key) > 0 else 100

# Error Correction and Privacy Amplification (Simulated)
def error_correction(alice_key, bob_key):
    return alice_key, bob_key

def privacy_amplification(key):
    key_length = len(key)
    final_key_length = key_length // 2
    return key[:final_key_length]

# Encrypt and Decrypt Messages
def encrypt_message(message, key):
    message_bytes = message.encode('utf-8')
    message_bits = ''.join(format(byte, '08b') for byte in message_bytes)
    key_bits = ''.join(str(bit) for bit in key)
    extended_key = (key_bits * ((len(message_bits) // len(key_bits)) + 1))[:len(message_bits)]
    encrypted_bits = ''.join(str(int(m_bit) ^ int(k_bit)) for m_bit, k_bit in zip(message_bits, extended_key))
    return encrypted_bits

def decrypt_message(encrypted_bits, key):
    key_bits = ''.join(str(bit) for bit in key)
    extended_key = (key_bits * ((len(encrypted_bits) // len(key_bits)) + 1))[:len(encrypted_bits)]
    decrypted_bits = ''.join(str(int(e_bit) ^ int(k_bit)) for e_bit, k_bit in zip(encrypted_bits, extended_key))
    # Convert bits back to bytes
    byte_array = bytearray()
    for i in range(0, len(decrypted_bits), 8):
        byte = decrypted_bits[i:i+8]
        if len(byte) == 8:
            byte_array.append(int(byte, 2))
    message = byte_array.decode('utf-8', errors='ignore')
    return message

# Extract text from PDF
def extract_text_from_pdf(file_stream):
    text = ""
    reader = PyPDF2.PdfReader(file_stream)
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        if user.lower() in ['hospital 1', 'hospital 2']:
            session['username'] = user.lower()
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username. Please log in as Hospital 1 or Hospital 2.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    user = session['username']
    if user == 'hospital 1':
        if request.method == 'POST':
            file = request.files['file']
            if file and file.filename.endswith('.pdf'):
                file_stream = io.BytesIO(file.read())
                file_content = extract_text_from_pdf(file_stream)
                uploaded_files['hospital 1'] = file_content
                flash('File uploaded successfully.')
                return redirect(url_for('transfer'))
            else:
                flash('Invalid file format. Please upload a PDF file.')
        return render_template('hospital1_dashboard.html')
    elif user == 'hospital 2':
        hospital2_received_file = received_files.get('hospital 2', None)
        if hospital2_received_file:
            # Decrypt the message
            encrypted_content, hospital2_key = hospital2_received_file
            decrypted_content = decrypt_message(encrypted_content, hospital2_key)
        else:
            decrypted_content = None
        return render_template('hospital2_dashboard.html', file_content=decrypted_content)
    else:
        flash('Unknown user.')
        return redirect(url_for('login'))

@app.route('/transfer')
def transfer():
    if 'username' not in session or session['username'] != 'hospital 1':
        flash('Access denied.')
        return redirect(url_for('login'))
    if 'hospital 1' not in uploaded_files:
        flash('No file to transfer.')
        return redirect(url_for('dashboard'))
    # Run QKD simulation
    alice_bits = generate_random_bits(NUM_QUBITS)
    alice_bases = generate_random_bases(NUM_QUBITS)
    qubits = prepare_qubits(alice_bits, alice_bases)
    bob_bases = generate_random_bases(NUM_QUBITS)
    bob_bits = measure_qubits(qubits, bob_bases)
    matching_indices = compare_bases(alice_bases, bob_bases)
    alice_key = sift_key(alice_bits, matching_indices)
    bob_key = sift_key(bob_bits, matching_indices)
    if len(alice_key) < 10:
        flash('Key exchange failed due to insufficient key length.')
        return redirect(url_for('dashboard'))
    qber = calculate_qber(alice_key, bob_key)
    if qber < QBER_THRESHOLD:
        alice_key_corrected, bob_key_corrected = error_correction(alice_key, bob_key)
        alice_final_key = privacy_amplification(alice_key_corrected)
        bob_final_key = privacy_amplification(bob_key_corrected)
        # Encrypt the file content
        file_content = uploaded_files['hospital 1']
        encrypted_content = encrypt_message(file_content, alice_final_key)
        # Store encrypted content for Hospital 2
        received_files['hospital 2'] = (encrypted_content, bob_final_key)
        flash('File transferred securely to Hospital 2.')
        flash(f'QBER : {qber:.2f}%')
    else:
        flash(f'Key exchange failed. QBER is {qber:.2f}%.')
    return redirect(url_for('dashboard'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)