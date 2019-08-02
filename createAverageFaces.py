# Create average faces
# One average face for each of the Fortune 100 companies

import pandas as pd
import matplotlib.pyplot as plt
from facer import facer
import time
import os

"""
  For each company:
    1. Load the saved images
    2. Combine the faces
    3. Save the average face
"""

def save_labeled_face_image(rank, company, image):
    # Plot the image
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(image)

    # Add a title
    kwargs = {"fontsize": 22, "fontweight": "heavy", "color": "gray", "alpha":0.9}
    title = f"{company}\nForbes Rank: #{rank}"
    ax.set_title(title, **kwargs)

    # Touch up the image
    ax.set(**{"xlabel": '', "ylabel": '', "xticks": [], "yticks": []})
    plt.tight_layout()

    # Save the image
    fp = os.path.join("average_faces", f"average_face_{rank:02.0f}_{company}_labeled.png")
    fig.savefig(fp, dpi=300)
    return

def create_average_face(rank, company):
    folder = f"./images/{rank:02.0f}_{company.replace(' ', '_')}/"
    print(f"Target folder: {folder}")
    images = facer.load_images(folder, verbose=True)
    if len(images) == 0:
        return

    # Detect landmarks for each face
    landmarks, faces = facer.detect_face_landmarks(images, verbose=True)

    # Use  the detected landmarks to create an average face
    fp = os.path.join("average_faces", f"average_face_{rank:02.0f}_{company}.jpg")
    average_face = facer.create_average_face(faces, landmarks, output_file=fp, save_image=True)

    # Save a labeled version of the average face
    save_labeled_face_image(rank, company, average_face)
    return


if __name__ == "__main__":
    # Load the Fortune 100 DataFrame
    fortune = (pd.read_csv("./Fortune100.csv")
                 .set_index("RANK"))

    # Create an average face for each company
    N = 75
    t0 = time.time()
    for rank, company in fortune.tail(N)["NAME"].items():
        print(f"({rank:02.0f}/{N}): {company}\n")
        try:
            create_average_face(rank, company)
        except Exception as e:
            print(f"Error: {e}\nSkipping company.\n\n")
    msg = f"All done! Total time elapsed: {(time.time() - t0) / 60:.2f} minutes."
    print(msg)
