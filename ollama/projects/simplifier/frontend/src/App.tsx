import { useEffect, useRef, useState } from "react";
import "./App.css";
import clsx from "clsx";

interface IMessage {
  source: "user" | "backend";
  message: string;
  timeStamp: string; //timestamp in ISO string format
}

const WS_ENDPOINT = "ws://127.0.0.1:8000/ws";

function App() {
  const [data, setData] = useState<{
    currentMessage: IMessage | null;
    messages: IMessage[] | [];
    ws: WebSocket | null;
  }>({
    currentMessage: null,
    messages: [],
    ws: null,
  });
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  function sendMessage(message: string) {
    data.ws?.send(message);
  }

  useEffect(() => {
    const ws = new WebSocket(WS_ENDPOINT);
    ws.onmessage = function (event) {
      // responseDate will be in format { content:string, time:string }
      const responseData: { time: string; content: string } = JSON.parse(
        event.data
      );

      setData((data) => {
        const responseMessage: IMessage = {
          source: "backend",
          message: responseData.content,
          timeStamp: responseData.time,
        };
        return {
          ...data,
          messages: [...data.messages, responseMessage],
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

  function textAreaIncrease() {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height =
      5 + textareaRef.current.scrollHeight + "px";
  }

  function textAreaReset() {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = "21px";
  }

  return (
    <>
      <div className="container">
        <section className="messagesSection">
          {data.messages.map((message, idx) => {
            return (
              <div
                key={`${idx}+${message}`}
                className={clsx(
                  "message",
                  message.source === "backend"
                    ? "backendMessage"
                    : "userMessage"
                )}
              >
                {message.message}
              </div>
            );
          })}
        </section>
        <section>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (
                data.currentMessage &&
                data.currentMessage.message.trim().length > 0
              ) {
                sendMessage(data.currentMessage.message);
                setData((data) => ({
                  ...data,
                  messages: [...data.messages, data.currentMessage!],
                  currentMessage: null,
                }));
              }
            }}
          >
            <textarea
              ref={textareaRef}
              rows={1}
              value={data.currentMessage ? data.currentMessage.message : ""}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.shiftKey) {
                  textAreaIncrease();
                  return;
                }
                if (
                  e.key === "Enter" &&
                  data.currentMessage &&
                  data.currentMessage.message.trim().length > 0
                ) {
                  sendMessage(data.currentMessage.message);
                  setData((data) => ({
                    ...data,
                    messages: [...data.messages, data.currentMessage!],
                    currentMessage: null,
                  }));
                  textAreaReset();
                }
              }}
              onChange={(e) => {
                if (e.target.value.trim() === "") {
                  textAreaReset();
                  setData((data) => ({
                    ...data,
                    currentMessage: {
                      message: e.target.value.trim(),
                      source: "user",
                      timeStamp: new Date().toISOString(),
                    },
                  }));
                  return;
                }
                setData((data) => ({
                  ...data,
                  currentMessage: {
                    message: e.target.value,
                    source: "user",
                    timeStamp: new Date().toISOString(),
                  },
                }));
              }}
            />
            <button type="submit">Send</button>
          </form>
        </section>
      </div>
    </>
  );
}

export default App;
