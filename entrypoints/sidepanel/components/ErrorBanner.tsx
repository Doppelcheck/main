export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-3 rounded-md border border-disagree/30 bg-disagree/10 p-2 text-sm text-disagree">
      {message}
    </div>
  );
}
