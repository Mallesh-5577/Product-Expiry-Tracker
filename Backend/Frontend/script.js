const API = "http://127.0.0.1:1000";

document.getElementById("medicineForm").onsubmit = async (e) => {
  e.preventDefault();

  const data = {
    name: document.getElementById("name").value,
    batch: document.getElementById("batch").value,
    expiry: document.getElementById("expiry").value,
    barcode: document.getElementById("barcode").value,
    quantity: parseInt(document.getElementById("quantity").value)
  };

  try {
    const res = await fetch(API + "/add", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const error = await res.json();
      alert("Error: " + error.error);
      return;
    }

    document.getElementById("medicineForm").reset();
    loadMedicines();
  } catch (e) {
    alert("Failed to connect to server. Make sure backend is running!");
    console.error(e);
  }
};

async function loadMedicines() {
  try {
    const res = await fetch(API + "/medicines");
    
    if (!res.ok) {
      throw new Error("Failed to fetch medicines: " + res.status);
    }
    
    const meds = await res.json();
    medicineList.innerHTML = "";

    if (!Array.isArray(meds)) {
      medicineList.innerHTML = "<p>Error loading medicines</p>";
      return;
    }

    if (meds.length === 0) {
      medicineList.innerHTML = "<p>No medicines added yet</p>";
      return;
    }

    meds.forEach(m => {
      medicineList.innerHTML += `
        <div class="card ${m.status}">
          <h3>${m.name}</h3>
          <p>Batch: ${m.batch}</p>
          <p>Expiry: ${m.expiry}</p>
          <p>Days Left: ${m.days_left}</p>
          <button onclick="deleteMed(${m.id})">Delete</button>
        </div>`;
    });
  } catch (e) {
    medicineList.innerHTML = "<p style='color:red'>⚠️ Cannot connect to server. Make sure backend is running on http://127.0.0.1:1000</p>";
    console.error(e);
  }
}

async function deleteMed(id) {
  try {
    const res = await fetch(API + "/delete/" + id, { method: "DELETE" });
    
    if (!res.ok) {
      const error = await res.json();
      alert("Error: " + error.error);
      return;
    }
    
    loadMedicines();
  } catch (e) {
    alert("Failed to delete medicine");
    console.error(e);
  }
}

loadMedicines();
