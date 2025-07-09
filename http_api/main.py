import socket
import math
from flask import Flask, request, jsonify
import os

app = Flask(__name__)

def ip_to_int(ip):
    return int.from_bytes(socket.inet_aton(ip), 'big')

def int_to_ip(num):
    return socket.inet_ntoa(num.to_bytes(4, 'big'))

def next_power_of_two(x):
    if x <= 1:
        return 1
    return 1 << (x - 1).bit_length()

@app.route('/partition', methods=['POST'])
def partition():
    data = request.get_json()
    if not data or 'subnet' not in data or 'dim' not in data:
        return jsonify({"error": "Invalid input"}), 400
    
    subnet_str = data['subnet']
    dim = data['dim']
    
    try:
        ip_part, mask_str = subnet_str.split('/')
        mask_val = int(mask_str)
        base_ip_int = ip_to_int(ip_part)
        total_size = 1 << (32 - mask_val)
    except Exception as e:
        return jsonify({"error": f"Invalid subnet: {str(e)}"}), 400

    reqs = []
    for idx, n in enumerate(dim):
        if n < 0:
            return jsonify({"error": f"Negative node count at index {idx}"}), 400
        
        required_size = n + 2
        block_size = next_power_of_two(required_size)
        k = block_size.bit_length() - 1
        subnet_mask = 32 - k
        reqs.append((idx, n, block_size, subnet_mask))
    
    reqs.sort(key=lambda x: (-x[2], x[0]))
    
    free_blocks = [(base_ip_int, base_ip_int + total_size)]
    results = [None] * len(dim)
    
    for idx, n, block_size, mask_val in reqs:
        found = False
        for block in free_blocks[:]:
            s, e = block
            remainder = s % block_size
            aligned_start = s if remainder == 0 else s + block_size - remainder
            
            if aligned_start + block_size <= e:
                free_blocks.remove(block)
                if aligned_start > s:
                    free_blocks.append((s, aligned_start))
                if aligned_start + block_size < e:
                    free_blocks.append((aligned_start + block_size, e))
                
                subnet_ip = int_to_ip(aligned_start)
                results[idx] = f"{subnet_ip}/{mask_val}"
                found = True
                break
        
        if not found:
            return jsonify({"error": "Not enough space to allocate all subnets"}), 400
    
    output = {f"LAN{i+1}": results[i] for i in range(len(dim))}
    return jsonify(output)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)