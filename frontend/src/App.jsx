import { BrowserRouter, Route, Routes } from 'react-router-dom';

import { Layout } from './components/Layout.jsx';
import { PracticePage } from './pages/PracticePage.jsx';
import { SegmentListPage } from './pages/SegmentListPage.jsx';
import { VideoListPage } from './pages/VideoListPage.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<VideoListPage />} />
          <Route path="/videos/:id" element={<SegmentListPage />} />
          <Route path="/videos/:id/segments/:position" element={<PracticePage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
