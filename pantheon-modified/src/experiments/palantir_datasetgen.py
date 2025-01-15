import os
import pickle
import numpy as np

def parse_one_way_delay(fname: str) -> float:
    """
    Parse the one-way delay from the filename.
    Example filename: hybla_wired96-4x-u-7s-plus-10_80_640_0_cwnd.txt
    We assume the one-way delay is the second underscore-separated token (e.g., '80').
    Adjust if your naming pattern is different.
    """
    parts = fname.split('_')
    # Example: ["hybla", "wired96-4x-u-7s-plus-10", "80", "640", "0", "cwnd.txt"]
    # If the one-way delay is indeed at index 1 or 2, adjust as needed.
    return float(parts[2])  # If '80' is at index 2, change to parts[2].

def build_dataset_from_traces(trace_dir: str, save_path: str = "/mydata/ccbench-dataset/6col.p"):
    """
    Reads all .txt files in `trace_dir`, extracts chunks of shape (10,6),
    and saves a combined dataset of shape (N,10,6) to `save_path` (as a pickle file).
    Then prints the 10th, 20th, ..., 90th percentiles for each feature.
    """
    data_list = []

    # Traverse all files in the directory
    for fname in os.listdir(trace_dir):
        if not fname.endswith(".txt"):
            continue  # Skip non-text files

        one_way_delay = parse_one_way_delay(fname)    # e.g., 80.0
        two_owd = 2.0 * one_way_delay                 # e.g., 160.0

        filepath = os.path.join(trace_dir, fname)
        with open(filepath, "r") as f:
            lines = f.readlines()

        # Process in chunks of 10 lines
        for i in range(0, len(lines), 10):
            chunk = lines[i:i+10]
            if len(chunk) < 10:
                # Skip incomplete chunk
                break

            # Each chunk -> shape (10,6)
            chunk_data = []
            for line in chunk:
                cols = line.split()

                # Extract columns (1-based indexing -> 0-based in Python)
                col3   = float(cols[2])   # "column 3"
                col4   = float(cols[3])   # "column 4"
                col8   = float(cols[7])   # "column 8"
                col68  = float(cols[67])  # "column 68"
                col77  = float(cols[76])  # "column 77"

                # Build the 6-element vector for this line
                row_vector = [
                    two_owd/100,   # 2 × one-way delay
                    col3,
                    col4,
                    col8,
                    col68,
                    col77
                ]
                chunk_data.append(row_vector)

            # Append one (10,6) chunk
            data_list.append(chunk_data)

    # Convert to NumPy array: shape (num_chunks, 10, 6)
    dataset = np.array(data_list, dtype=np.float32)

    # Print final shape
    print("Final dataset shape:", dataset.shape)

    # ------------------------------------------------------
    # Print the 10th, 20th, ..., 90th percentiles per feature
    # ------------------------------------------------------
    percentiles = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    n_features = dataset.shape[2]  # 6 in this case

    print("\nPercentiles for each feature:")
    for feat_idx in range(n_features):
        # Flatten all lines (N * 10) for this feature
        col_data = dataset[:, :, feat_idx].ravel()
        print(f"Feature {feat_idx+1}:")
        for p in percentiles:
            val = np.percentile(col_data, p)
            print(f"  {p}th percentile: {val:.4f}")
        print("")

    # ------------------------------------------------------
    # Save dataset to pickle file
    # ------------------------------------------------------
    with open(save_path, "wb") as f:
        pickle.dump(dataset, f)

    print(f"Dataset saved to {save_path}")

if __name__ == "__main__":
    TRACE_DIR = "/mydata/ccbench-traces"
    OUTPUT_PATH = "/mydata/ccbench-dataset/6col-time-based.p"

    build_dataset_from_traces(TRACE_DIR, OUTPUT_PATH)
