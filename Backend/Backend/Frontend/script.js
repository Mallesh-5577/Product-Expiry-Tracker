// Dynamically set API based on environment
const API = (window.location.protocol === 'file:' || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? "http://localhost:1000"
  : window.location.origin;

function showAuthMessage(message) {
  const list = document.getElementById('productList');
  if (list) {
    list.innerHTML = `<p class='state-message state-error'>${message}</p>`;
  }
}

function updateInventoryCount(count) {
  const countNode = document.getElementById('inventoryCount');
  if (countNode) {
    countNode.textContent = `${count} item${count === 1 ? '' : 's'}`;
  }
}

// Check if user is logged in
document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('token');
  if (!token) {
    updateInventoryCount(0);
    window.location.href = '/auth';
    return;
  }

  loadProducts();
});

document.getElementById("productForm").onsubmit = async (e) => {
  e.preventDefault();

  const token = localStorage.getItem('token');
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
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(data)
    });

    if (res.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/auth';
      return;
    }

    if (!res.ok) {
      const error = await res.json();
      alert("Error: " + error.error);
      return;
    }

    document.getElementById("productForm").reset();
    loadProducts();
  } catch (e) {
    alert("Failed to connect to server. Make sure backend is running!");
    console.error(e);
  }
};

async function loadProducts() {
  const token = localStorage.getItem('token');
  const productList = document.getElementById('productList');

  if (!productList) {
    return;
  }

  try {
    const res = await fetch(API + "/products", {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
    
    if (res.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/auth';
      return;
    }

    if (!res.ok) {
      throw new Error("Failed to fetch products: " + res.status);
    }

    const products = await res.json();
    productList.innerHTML = "";

    if (!Array.isArray(products)) {
      productList.innerHTML = "<p class='state-message state-error'>Error loading products</p>";
      return;
    }

    if (products.length === 0) {
      productList.innerHTML = "<p class='state-message'>No products added yet</p>";
      updateInventoryCount(0);
      return;
    }

    updateInventoryCount(products.length);

    products.forEach((product, index) => {
      productList.innerHTML += `
        <div class="card ${product.status}" style="animation-delay:${Math.min(index * 90, 540)}ms">
          <h3>${product.name}</h3>
          <p>Batch: ${product.batch}</p>
          <p>Expiry: ${product.expiry}</p>
          <p>Barcode: ${product.barcode}</p>
          <p>Quantity: ${product.quantity}</p>
          <p>Days Left: ${product.days_left}</p>
          <button onclick="deleteProduct(${product.id})">Delete</button>
        </div>`;
    });
  } catch (e) {
    productList.innerHTML = "<p class='state-message state-error'>⚠️ Cannot connect to server.</p>";
    updateInventoryCount(0);
    console.error(e);
  }
}

async function deleteProduct(id) {
  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API + "/products/" + id, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });
    
    if (res.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/auth';
      return;
    }

    if (!res.ok) {
      const error = await res.json();
      alert("Error: " + error.error);
      return;
    }
    
    loadProducts();
  } catch (e) {
    alert("Failed to delete product");
    console.error(e);
  }
}

function logout() {
  localStorage.removeItem('token');
  window.location.href = '/';
}
