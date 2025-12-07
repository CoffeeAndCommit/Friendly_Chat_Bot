<template>
  <div class="min-h-screen flex flex-col items-center justify-center bg-gray-100 p-4">
    <div class="w-full max-w-md bg-white rounded-2xl shadow p-4">
      
      <!-- Header -->
      <div class="flex items-center gap-3 border-b pb-3 mb-3">
        <div class="text-3xl">🤖</div>
        <div>
          <h2 class="text-xl font-semibold">AIRA Bot</h2>
          <p class="text-sm text-gray-500">Your AI friend</p>
        </div>
      </div>

      <!-- Chat Messages -->
      <div class="h-80 overflow-y-auto space-y-3 mb-3 pr-2">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          :class="msg.isBot ? 'text-left' : 'text-right'"
        >
          <p
            :class="[
              'inline-block px-4 py-2 rounded-xl text-sm',
              msg.isBot ? 'bg-gray-200' : 'bg-blue-500 text-white'
            ]"
          >
            {{ msg.text }}
          </p>
        </div>
      </div>

      <!-- Input -->
      <div class="flex items-center gap-2">
        <input
          v-model="input"
          type="text"
          placeholder="Type a message..."
          class="flex-1 border p-2 rounded-lg focus:outline-none"
          @keyup.enter="sendMessage"
        />
        <button
          @click="sendMessage"
          class="bg-blue-600 text-white px-4 py-2 rounded-xl"
        >
          Send
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";

const messages = ref([
  { text: "Hi! I'm AIRA Bot 👋", isBot: true }
]);

const input = ref("");
let socket = null;

onMounted(() => {
  // Replace later with real user id
  const wsUrl = "ws://localhost:5173/ws/chat/123/";

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket connected");
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    messages.value.push({ text: data.message, isBot: true });
  };

  socket.onerror = (err) => console.error("WS error:", err);
});

function sendMessage() {
  if (!input.value.trim()) return;

  const text = input.value;
  messages.value.push({ text, isBot: false });

  socket.send(JSON.stringify({ message: text }));
  input.value = "";
}
</script>

<style scoped>
/* Optional extra styling */
</style>
