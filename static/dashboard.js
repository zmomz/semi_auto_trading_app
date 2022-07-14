Vue.use(BootstrapVue)

new Vue({
    data: function () {
        return {
            fields:['id','symbol','type','price','actions'],
            items: []
        }
    },

    methods: {
        async loadData() {
            const gResponse = await fetch("/trades/data/vue");
            const gObject = await gResponse.json();
            this.items = gObject.orders;
            return this.items
        },
        rowClass(item, type) {
            if (!item || type !== 'row') return
            if (item.type === "limit buy") return 'table-success'
        },
        redirect_new(){
            window.location.href = '/'
          },
        redirect_pause(){
            window.location.href = '/paused'
        }
        ,
        async cancel(id, pair) {
            const res = await fetch('/trades/cancel', {
                method: 'POST',
                headers: {
                    'Content-type': 'application/json',
                },
                body: JSON.stringify({ id: id, symbol: pair })
            }).then(location.reload())
        },
        async cancel_market(id, pair) {
            const res = await fetch('/trades/cancelandsellmarket', {
                method: 'POST',
                headers: {
                    'Content-type': 'application/json',
                },
                body: JSON.stringify({ id: id, symbol: pair })
            }).then(location.reload())
        },
        async pause_all() {
            const res = await fetch('/trades/pause', {
                method: 'POST',
                headers: {
                    'Content-type': 'application/json',
                },
                body: JSON.stringify(this.items)
            }).then(location.reload())
        },
    },
    created: async function () {
        createddata = await this.loadData()
        console.log(createddata)
    },
    el: '#app',
    delimiters: ['[[', ']]']
})
