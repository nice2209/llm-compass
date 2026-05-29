import DefaultTheme from "vitepress/theme";
import type { Theme } from "vitepress";
import PriceTable from "./PriceTable.vue";

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // 마크다운에서 <PriceTable /> 로 전역 사용
    app.component("PriceTable", PriceTable);
  },
} satisfies Theme;
