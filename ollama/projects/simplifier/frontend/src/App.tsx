import { useEffect, useState } from "react";

function App() {
  const [data, setData] = useState<{
    currentMessage: string;
    messages: Record<string, string> | null;
    ws: WebSocket | null;
  }>({
    currentMessage: "",
    messages: null,
    ws: null,
  });

  function sendMessage(message: string) {
    data.ws?.send(message);
  }

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws");
    ws.onmessage = function (event) {
      // responseDate will be in format { content:string}
      const responseData: { time: string; content: string } = JSON.parse(
        event.data
      );
      console.log(responseData, responseData.time);
      setData((data) => {
        const updatedMessages = data.messages ?? {};
        updatedMessages[responseData.time] =
          updatedMessages[responseData.time] ?? "" + responseData.content;
        console.log(updatedMessages);
        return {
          ...data,
          messages: updatedMessages,
        };
      });
    };

    ws.onopen = () => {
      console.log("connected");
      setData((data) => ({ ...data, ws: ws }));
    };

    ws.onclose = () => {
      console.log("closed");
    };

    return () => {
      console.log("closing");
      ws.close();
    };
  }, []);

  return (
    <>
      <div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(data.currentMessage);
            setData((data) => ({ ...data, currentMessage: "" }));
          }}
        >
          <input
            type="text"
            value={data.currentMessage}
            onChange={(e) =>
              setData((data) => ({ ...data, currentMessage: e.target.value }))
            }
          />
          <button type="submit">Send</button>
        </form>
        <div>{JSON.stringify(data.messages)}</div>
      </div>
    </>
  );
}

export default App;
