import argparse
import pandas as pd

def view_top_titles(csv_path: str, cluster_id: int, top_n: int = 20):
    # Load the clustered data
    df = pd.read_csv(csv_path)

    # Check that necessary columns exist
    if "title_y" not in df.columns or "product_cluster" not in df.columns:
        raise ValueError("CSV must contain 'title_y' and 'product_cluster' columns.")

    # Filter rows matching the cluster ID
    subset = df[df["product_cluster"] == cluster_id]

    if subset.empty:
        print(f"No products found for cluster {cluster_id}.")
        return

    # Count occurrences of each product title
    top_titles = (
        subset["title_y"]
        .value_counts()
        .head(top_n)
    )

    print(f"\nTop {top_n} product titles in cluster {cluster_id}:\n")
    for i, (title, count) in enumerate(top_titles.items(), start=1):
        print(f"{i:2d}. {title}  (count: {count})")

    print(f"\nTotal products in cluster {cluster_id}: {len(subset)}")


def main():
    parser = argparse.ArgumentParser(description="View top product titles for a given cluster ID.")
    parser.add_argument("--input", default="./data/products_clustered.csv")
    parser.add_argument("--cluster", type=int, default=38, help="Cluster ID to inspect.")
    parser.add_argument("--top", type=int, default=20, help="Number of top titles to display.")
    args = parser.parse_args()

    view_top_titles(args.input, args.cluster, args.top)


if __name__ == "__main__":
    main()
