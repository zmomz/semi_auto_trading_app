Vue.use(BootstrapVue)

new Vue({
    data: function () {
        return {
            fields:['id','symbol','type','price'],
            items: []
        }
    },

    methods: {
        async loadData() {
            const gResponse = await fetch("/paused/data/vue");
            const gObject = await gResponse.json();
            this.items = gObject.orders;
            return this.items
        },
        rowClass(item, type) {
            if (!item || type !== 'row') return
            if (item.type === "limit buy") return 'table-success'
        },
        async activate_orders(){
            const res = await fetch('/paused/activate', {
                method: 'POST',
                headers: {
                    'Content-type': 'application/json',
                },
                body: JSON.stringify({ 'activate':'all' })
            }).then(location.reload())
        }
        ,
        redirect_new(){
            window.location.href = '/'
          }
        ,
        redirect_open(){
            window.location.href='/trades'
        }
        ,
    },
    created: async function () {
        createddata = await this.loadData()
        console.log(createddata)
    },
    el: '#app',
    delimiters: ['[[', ']]']
})
