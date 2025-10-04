export interface OrderItem {
  title: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  date: string;
  total: number;
  status: "Processing" | "Shipped" | "Delivered";
  items: OrderItem[];
}

export async function fetchUserOrders(): Promise<Order[]> {
  // Mock API call
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: "ORD-001",
          date: "2024-07-01",
          total: 39.97,
          status: "Delivered",
          items: [
            { title: "The Great Gatsby", quantity: 1, price: 12.99 },
            { title: "1984", quantity: 1, price: 9.99 },
            { title: "To Kill a Mockingbird", quantity: 1, price: 16.99 }
          ]
        },
        {
          id: "ORD-002",
          date: "2024-07-10",
          total: 24.99,
          status: "Processing",
          items: [{ title: "Pride and Prejudice", quantity: 1, price: 24.99 }]
        }
      ]);
    }, 800);
  });
}

export function generateInvoice(order: Order) {
  const invoiceContent = `
BookHaven Invoice
===========================
Order ID: ${order.id}
Order Date: ${order.date}
Status: ${order.status}

Items:
${order.items.map((i) => `- ${i.title} (x${i.quantity}) - $${i.price}`).join("\n")}

Total: $${order.total.toFixed(2)}
===========================
Thank you for shopping with BookHaven!
  `;
  const blob = new Blob([invoiceContent], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${order.id}_invoice.txt`;
  link.click();
}