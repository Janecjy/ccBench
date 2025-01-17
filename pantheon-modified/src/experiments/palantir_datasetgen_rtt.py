import os
import pickle
import numpy as np

def parse_one_way_delay(fname: str) -> float:
    """
    Parse the one-way delay from the filename.
    Example filename: hybla_wired96-4x-u-7s-plus-10_80_640_0_cwnd.txt
    Adjust indices if your naming pattern differs.
    """
    parts = fname.split('_')
    # Example: ["hybla", "wired96-4x-u-7s-plus-10", "80", "640", "0", "cwnd.txt"]
    # If the OWD is at index 2 for '80':
    return float(parts[2])  # e.g., 80.0


def count_valid_rtt_blocks(lines, two_owd) -> int:
    """
    Counts how many valid (10,6) blocks can be formed for this file
    in RTT-based mode, WITHOUT actually building the blocks.
    
    Each block = 10 RTT-chunks, each RTT-chunk = lines_per_rtt lines.
    We'll do the same validity checks (column count, etc.).
    """
    lines_per_rtt = int(two_owd / 10.0)  # each line = 10 ms
    chunk_size_in_lines = 10 * lines_per_rtt

    num_valid = 0
    n = len(lines)
    
    # We'll move in steps of chunk_size_in_lines
    for start in range(0, n, chunk_size_in_lines):
        if start + chunk_size_in_lines > n:
            break  # incomplete block of 10 RTT-chunks

        valid_block = True

        # For each of the 10 RTT-chunks in this block
        for rtt_idx in range(10):
            sub_start = start + rtt_idx * lines_per_rtt
            sub_end   = sub_start + lines_per_rtt
            # check each line
            for line in lines[sub_start : sub_end]:
                cols = line.split()
                if len(cols) < 77:
                    valid_block = False
                    break
            if not valid_block:
                break

        if valid_block:
            num_valid += 1

    return num_valid


def build_limited_rtt_blocks(lines, two_owd, limit) -> np.ndarray:
    """
    Actually builds up to `limit` valid (10,6) blocks
    in RTT-based mode for one file.
    
    Each block = 10 RTT-chunks => shape (10,6).
    Returns an array of shape (<=limit, 10, 6).
    """
    lines_per_rtt = int(two_owd / 10.0)  # each line = 10 ms
    chunk_size_in_lines = 10 * lines_per_rtt

    chunks = []
    n = len(lines)

    for start in range(0, n, chunk_size_in_lines):
        if len(chunks) >= limit:
            break  # we've reached the limit for this file

        if start + chunk_size_in_lines > n:
            break  # incomplete block

        valid_block = True
        block_data = []  # store the 10 RTT-chunk rows

        for rtt_idx in range(10):
            sub_start = start + rtt_idx * lines_per_rtt
            sub_end   = sub_start + lines_per_rtt

            # We'll gather columns 3,4,8,68,77 for averaging
            col3_vals   = []
            col4_vals   = []
            col8_vals   = []
            col68_vals  = []
            col77_vals  = []

            # Check each line in this sub-block
            for line in lines[sub_start : sub_end]:
                cols = line.split()
                if len(cols) < 77:
                    valid_block = False
                    break
                col3_vals.append(float(cols[2]))
                col4_vals.append(float(cols[3]))
                col8_vals.append(float(cols[7]))
                col68_vals.append(float(cols[67]))
                col77_vals.append(float(cols[76]))
            if not valid_block:
                break

            # average them
            avg_col3  = np.mean(col3_vals)
            avg_col4  = np.mean(col4_vals)
            avg_col8  = np.mean(col8_vals)
            avg_col68 = np.mean(col68_vals)
            avg_col77 = np.mean(col77_vals)

            row_vector = [
                two_owd / 100.0,  # same scaling as time-based
                avg_col3,
                avg_col4,
                avg_col8,
                avg_col68,
                avg_col77
            ]
            block_data.append(row_vector)

        # if valid, we should have exactly 10 rows
        if valid_block and len(block_data) == 10:
            block_array = np.array(block_data, dtype=np.float32)  # shape (10,6)
            chunks.append(block_array)

    if chunks:
        file_dataset = np.stack(chunks, axis=0)  # (num_chunks, 10, 6)
    else:
        file_dataset = np.empty((0, 10, 6), dtype=np.float32)

    # We'll only build up to `limit`, so shape is (<=limit, 10, 6)
    return file_dataset


def build_dataset_rtt_same_num(trace_dir, save_path):
    """
    RTT-based approach where ALL files generate the SAME number of data points.
    
    Steps:
      1) For each file, count how many valid (10,6) blocks are possible.
      2) min_num_chunks = minimum of these counts across all files.
      3) For each file, actually build up to min_num_chunks blocks.
      4) Concatenate everything => shape (total_files * min_num_chunks, 10, 6).
      5) Save to pickle and print percentiles.
    """
    file_lines_map = {}      # store lines in memory so we don't read from disk twice
    file_twoowd_map = {}     # store 2*owd
    valid_counts = []

    # First pass: read lines, compute # valid chunks
    for fname in os.listdir(trace_dir):
        if not fname.endswith(".txt"):
            continue

        filepath = os.path.join(trace_dir, fname)
        with open(filepath, "r") as f:
            lines = f.readlines()

        # parse owd
        owd = parse_one_way_delay(fname)  # e.g., 80.0
        two_owd = 2.0 * owd               # e.g., 160.0

        # store in memory
        file_lines_map[fname] = lines
        file_twoowd_map[fname] = two_owd

    #     # count valid blocks
    #     count_blocks = count_valid_rtt_blocks(lines, two_owd)
    #     print(f"File: {fname}, valid blocks: {count_blocks}")
    #     valid_counts.append(count_blocks)

    # if not valid_counts:
    #     # no data
    #     print("No valid .txt files found! Exiting.")
    #     return

    # The min number of chunks across all files
    # min_num_chunks = min(valid_counts)
    min_num_chunks = 18
    print(f"Minimum valid RTT-blocks across all files: {min_num_chunks}")

    # Second pass: actually build up to min_num_chunks blocks per file
    all_files_data = []
    for fname in file_lines_map:
        lines = file_lines_map[fname]
        two_owd = file_twoowd_map[fname]

        file_dataset = build_limited_rtt_blocks(lines, two_owd, min_num_chunks)  
        print(f"File: {fname}, dataset shape: {file_dataset.shape}")
        # shape => (<= min_num_chunks, 10, 6)

        # We expect exactly 'min_num_chunks' if everything lines up.
        # If a file has fewer than 'min_num_chunks' valid blocks, that's okay:
        # it won't exceed the min anyway.
        if file_dataset.size > 0:
            all_files_data.append(file_dataset)
    
    # Combine => shape (num_files * min_num_chunks, 10, 6)
    if len(all_files_data) == 0:
        dataset = np.empty((0, 10, 6), dtype=np.float32)
    else:
        dataset = np.concatenate(all_files_data, axis=0)

    print("Final dataset shape:", dataset.shape)

    # --------------- PRINT PERCENTILES ---------------
    if dataset.size == 0:
        print("No data to compute percentiles.")
    else:
        flattened = dataset.reshape(-1, dataset.shape[-1])  # (N * 10, 6)
        percentiles = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        n_features = flattened.shape[1]

        print("\nPercentiles for each feature:")
        for feat_idx in range(n_features):
            col_data = flattened[:, feat_idx]
            print(f"Feature {feat_idx+1}:")
            for p in percentiles:
                val = np.percentile(col_data, p)
                print(f"  {p}th percentile: {val:.4f}")
            print("")

    # --------------- SAVE TO PICKLE ---------------
    with open(save_path, "wb") as f:
        pickle.dump(dataset, f)

    print(f"Dataset saved to {save_path}")


if __name__ == "__main__":
    TRACE_DIR = "/mydata/ccbench-traces"
    OUTPUT_PATH = "/mydata/ccbench-dataset/6col-rtt-same.p"

    build_dataset_rtt_same_num(TRACE_DIR, OUTPUT_PATH)
