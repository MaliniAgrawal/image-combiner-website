const MAX_FILE_SIZE = 2 * 1024 * 1024; // 2 MB

document.getElementById("uploadForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const image1 = document.getElementById("image1").files[0];
    const image2 = document.getElementById("image2").files[0];

    if (!image1 || !image2) {
        alert("Please select both images.");
        return;
    }

    if (image1.size > MAX_FILE_SIZE || image2.size > MAX_FILE_SIZE) {
        alert("Each file must be under 2MB.");
        return;
    }

    const formData = new FormData();
    formData.append("image1", image1);
    formData.append("image2", image2);

    try {
        // Display uploaded images
        document.getElementById("imagePreview1").src = URL.createObjectURL(image1);
        document.getElementById("imagePreview2").src = URL.createObjectURL(image2);

        // Call the API Gateway endpoint
        const response = await fetch("https://21pf3197la.execute-api.us-west-1.amazonaws.com/default/image-combiner-function", {
            method: "POST",
            body: formData,
            headers: {
                'Accept': 'image/jpeg',
                // Don't set Content-Type header - let the browser set it with the boundary
            },
        });

        if (response.ok) {
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);
            
            // Display combined image
            document.getElementById("combinedImage").src = imageUrl;
            
            // Set download link
            const downloadLink = document.getElementById("downloadLink");
            downloadLink.href = imageUrl;
            downloadLink.download = 'combined_image.jpg';
            downloadLink.style.display = "block";
        } else {
            const errorText = await response.text();
            alert(`Error combining images: ${errorText}`);
        }
    } catch (error) {
        console.error("Error:", error);
        alert("An error occurred. Please try again.");
    }
});